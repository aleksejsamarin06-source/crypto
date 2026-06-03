import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.core.audit.audit_logger import AuditLogger
from src.core.audit.log_formatters import LogFormatter
from src.core.audit.log_signer import AuditLogSigner
from src.core.audit.log_verifier import LogVerifier
from src.core.events import event_system
from src.core.import_export.formats.password_manager import PasswordManagerFormat
from src.core.key_manager import KeyManager
from src.core.security.memory_guard import SecretHolder, SecureMemory
from src.core.security.side_channel_protection import ConstantTimeOps, SecurityHardening
from src.core.settings_manager import SettingsManager
from src.database.db import Database


class TestSprint8Regression(unittest.TestCase):
    def setUp(self):
        os.environ["UNITTEST_RUNNING"] = "1"
        self.temp_files = []

    def tearDown(self):
        os.environ.pop("UNITTEST_RUNNING", None)
        for path in self.temp_files:
            if os.path.exists(path):
                os.unlink(path)

    def temp_path(self, suffix=".db"):
        file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        file.close()
        self.temp_files.append(file.name)
        return file.name

    def create_audit_db(self):
        db = Database(self.temp_path())
        db.connect()
        db.create_tables()
        logger = AuditLogger(db, "Sprint8Password!")
        logger.log_auth_event("LOGIN_SUCCESS", {"user_id": "tester"})
        logger.log_vault_event("ENTRY_CREATED", {"id": 7, "title": "Example"})
        logger.log_clipboard_event("CLIPBOARD_COPIED", {"source_entry_id": 7})
        logger.log_security_event("SUSPICIOUS_ACTIVITY", {"reason": "test"})
        logger.log_settings_change("auto_lock", "false", "true")
        return db, logger

    def test_key_manager_full_cycle_and_secure_zero(self):
        manager = KeyManager()
        stored_hash = manager.create_master_hash("Master123!")

        self.assertTrue(manager.verify_master_password("Master123!", stored_hash))
        self.assertFalse(manager.verify_master_password("Wrong123!", stored_hash))

        with self.assertRaises(ValueError):
            manager.encrypt_password("secret")
        with self.assertRaises(ValueError):
            manager.decrypt_password("00")

        manager.set_master_password("Master123!")
        encrypted = manager.encrypt_password("secret")
        self.assertEqual(manager.decrypt_password(encrypted), "secret")

        data = bytearray(b"secret")
        manager.secure_zero(data)
        self.assertEqual(data, bytearray(b"\x00" * 6))
        manager.secure_zero(b"secret")
        manager.secure_zero("secret")
        manager.set_encryption_key(b"0" * 32)
        self.assertEqual(manager.current_key, b"0" * 32)

    def test_audit_formatters_verifier_and_notifications(self):
        db, logger = self.create_audit_db()
        formatter = LogFormatter(db)

        entries = formatter.get_all_entries()
        self.assertGreaterEqual(len(entries), 6)

        json_path = self.temp_path(".json")
        csv_path = self.temp_path(".csv")
        signed_path = self.temp_path(".signed.json")
        self.assertEqual(formatter.export_json(json_path), json_path)
        self.assertEqual(formatter.export_csv(csv_path), csv_path)
        self.assertEqual(formatter.export_signed_json(signed_path, "public-key"), signed_path)

        exported = json.loads(open(signed_path, encoding="utf-8").read())
        self.assertEqual(exported["export_metadata"]["public_key"], "public-key")
        self.assertEqual(exported["export_metadata"]["total_entries"], len(entries))

        verifier = LogVerifier(db, "Sprint8Password!")
        self.assertTrue(verifier.check_integrity())
        report = verifier.get_verification_report()
        self.assertIn("ОТЧЁТ", report)
        self.assertTrue(verifier.verify_range(1, 2)["total"] >= 1)

        received = []
        event_system.subscribe("log_tampering_detected", lambda data: received.append(data))
        cursor = db.conn.cursor()
        cursor.execute("UPDATE audit_log SET signature = ? WHERE sequence_number = 2", ("00",))
        db.conn.commit()
        self.assertFalse(verifier.verify_and_notify())
        self.assertTrue(received)

        logger.disable()
        self.assertEqual(logger.get_next_sequence(), 0)
        self.assertEqual(logger.get_previous_hash(), "0" * 64)
        self.assertIsNone(logger.log_event("DISABLED", "INFO", "test", {}))
        logger.enable()
        db.close()

    def test_signer_fallback_and_error_paths(self):
        signer = AuditLogSigner()
        with self.assertRaises(ValueError):
            signer.sign(b"data")
        self.assertFalse(signer.verify(b"data", b"signature"))
        self.assertEqual(signer.get_public_key_hex(), "")

        with patch("src.core.audit.log_signer.ed25519.Ed25519PrivateKey.from_private_bytes", side_effect=ValueError):
            signer = AuditLogSigner("password")
        signature = signer.sign(b"data")
        self.assertTrue(signer.verify(b"data", signature))
        self.assertFalse(signer.verify(b"data", b"bad"))

    def test_settings_validation_and_limits(self):
        manager = SettingsManager(self.temp_path())
        manager.set_notification_enabled(False)
        self.assertFalse(manager.get_notification_enabled())

        manager.set_minimize_lock_mode("invalid")
        self.assertEqual(manager.get_minimize_lock_mode(), "delayed")
        manager.set_minimize_lock_delay_seconds(1)
        self.assertEqual(manager.get_minimize_lock_delay_seconds(), 60)

        manager.set_security_profile("paranoid")
        self.assertEqual(manager.get_security_profile(), "paranoid")
        self.assertEqual(manager.get_auto_lock_timeout_seconds(), 60)
        manager.set_security_profile("invalid")
        self.assertEqual(manager.get_security_profile(), "standard")

        manager.set_auto_lock_timeout_seconds(999999)
        self.assertEqual(manager.get_auto_lock_timeout_seconds(), 8 * 60 * 60)
        manager.set_activity_sensitivity("invalid")
        self.assertEqual(manager.get_activity_sensitivity(), "medium")
        manager.set_bool("side_channel_protection_enabled", False)
        manager.set_minimize_lock_mode("disabled")
        warnings = manager.validate_security_settings()
        self.assertGreaterEqual(len(warnings), 2)
        manager.close()

    def test_database_corruption_and_migration_paths(self):
        corrupt_path = self.temp_path()
        with open(corrupt_path, "wb") as file:
            file.write(b"CORRUPTED_DATA")
        with self.assertRaises(Exception):
            Database(corrupt_path).connect()

        db = Database(self.temp_path())
        db.connect()
        db.create_tables()
        db.migrate_if_needed()
        db.close()

        memory_db = Database()
        memory_db.create_tables()
        memory_db.close()

    def test_side_channel_memory_and_password_manager_format(self):
        self.assertTrue(ConstantTimeOps.compare_bytes(b"a", b"a"))
        self.assertFalse(ConstantTimeOps.compare_text("a", "b"))
        self.assertEqual(ConstantTimeOps.fixed_time_lookup("b", ["a", "b", "c"]), "b")
        self.assertIsNone(ConstantTimeOps.fixed_time_lookup("x", ["a", "b"]))
        ConstantTimeOps.random_delay(0)

        hardening = SecurityHardening(enabled=True, random_delay_ms=0)
        self.assertTrue(hardening.compare_secret("same", "same"))
        self.assertTrue(hardening.compare_secret_bytes(b"same", b"same"))
        disabled = SecurityHardening(enabled=False)
        self.assertFalse(disabled.compare_secret("a", "b"))
        self.assertFalse(disabled.compare_secret_bytes(b"a", b"b"))

        memory = SecureMemory()
        buffer = memory.allocate_secure(4)
        memory.secure_zero(buffer, 4)
        memory.free_secure(buffer, 4)
        holder = SecretHolder(b"secret")
        self.assertEqual(holder.get_data(), b"secret")
        holder.wipe()

        formatter = PasswordManagerFormat()
        bitwarden = formatter.dump_bitwarden([{
            "title": "Site",
            "username": "user",
            "password": "pass",
            "url": "https://example.com",
            "notes": "note",
            "category": "work",
        }])
        loaded = formatter.load_bitwarden(json.dumps(bitwarden))
        self.assertEqual(loaded[0]["title"], "Site")
        csv_loaded = formatter.load_lastpass_csv("title,username,password,url,notes,category\n,me,p,https://a,,\n")
        self.assertEqual(csv_loaded[0]["title"], "https://a")


if __name__ == "__main__":
    unittest.main()
