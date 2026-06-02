import os
import tempfile
import unittest

os.environ['UNITTEST_RUNNING'] = '1'

from src.core.import_export.exporter import VaultExporter
from src.core.import_export.importer import VaultImporter
from src.core.import_export.key_exchange import KeyExchangeService, QRCodeService
from src.core.import_export.sharing_service import SharingService
from src.core.key_manager import KeyManager
from src.core.vault.entry_manager import EntryManager
from src.database.db import Database


class Sprint6Fixture(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = Database(self.db_path)
        self.db.connect()
        self.db.create_tables()

        self.key_manager = KeyManager()
        self.key_manager.set_encryption_key(os.urandom(32))
        self.entry_manager = EntryManager(self.db, self.key_manager)
        self.entry_id = self.entry_manager.create_entry({
            "title": "GitHub",
            "username": "dev",
            "password": "secret",
            "url": "https://github.com",
            "notes": "token",
            "category": "work",
        })

    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)


class TestSprint6ImportExport(Sprint6Fixture):
    def test_encrypted_json_round_trip(self):
        exporter = VaultExporter(self.entry_manager)
        package = exporter.export_vault(password="export-pass")

        key_manager = KeyManager()
        key_manager.set_encryption_key(os.urandom(32))
        target_manager = EntryManager(self.db, key_manager)
        importer = VaultImporter(target_manager)

        result = importer.import_data(package, password="export-pass", mode="dry-run")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["preview"][0]["title"], "GitHub")

    def test_tampered_export_is_rejected(self):
        exporter = VaultExporter(self.entry_manager)
        package = exporter.export_vault(password="export-pass")
        package["data"] = package["data"][:-2] + "AA"

        importer = VaultImporter(self.entry_manager)

        with self.assertRaises(ValueError):
            importer.import_data(package, password="export-pass", mode="dry-run")

    def test_encrypted_json_import_without_password_has_clear_error(self):
        exporter = VaultExporter(self.entry_manager)
        package = exporter.export_vault(password="export-pass")
        importer = VaultImporter(self.entry_manager)

        with self.assertRaisesRegex(ValueError, "пароль импортируемого файла"):
            importer.import_data(package, mode="dry-run")

    def test_plain_csv_import_dry_run_sanitizes_content(self):
        csv_text = "title,username,password,url,notes\nBad,<script>x</script>,pw,javascript:https://x,ok\n"
        importer = VaultImporter(self.entry_manager)

        result = importer.import_data(csv_text, import_format="csv", mode="dry-run")

        self.assertEqual(result["total"], 1)
        self.assertNotIn("script", result["preview"][0]["username"].lower())
        self.assertNotIn("javascript", result["preview"][0]["url"].lower())

    def test_duplicate_create_import_adds_entries(self):
        exporter = VaultExporter(self.entry_manager)
        package = exporter.export_vault(password="export-pass")
        importer = VaultImporter(self.entry_manager)

        result = importer.import_data(package, password="export-pass", mode="merge", duplicate_strategy="create")

        self.assertEqual(result["imported"], 1)
        self.assertEqual(len(self.entry_manager.get_all_entries()), 2)

    def test_import_creates_missing_history_table_for_old_database(self):
        exporter = VaultExporter(self.entry_manager)
        package = exporter.export_vault(password="export-pass")
        cursor = self.db.conn.cursor()
        cursor.execute("DROP TABLE import_export_history")
        self.db.conn.commit()

        importer = VaultImporter(self.entry_manager)
        result = importer.import_data(package, password="export-pass", mode="merge", duplicate_strategy="create")

        self.assertEqual(result["imported"], 1)
        cursor.execute("SELECT COUNT(*) FROM import_export_history")
        self.assertGreater(cursor.fetchone()[0], 0)

    def test_bitwarden_export_shape(self):
        exporter = VaultExporter(self.entry_manager)
        data = exporter.export_vault(export_format="bitwarden_json", allow_plaintext=True)

        self.assertIn("items", data)
        self.assertEqual(data["items"][0]["login"]["username"], "dev")

    def test_csv_export_without_password_requires_plaintext_flag(self):
        exporter = VaultExporter(self.entry_manager)

        with self.assertRaisesRegex(ValueError, "пароль экспорта"):
            exporter.export_vault(export_format="csv")


class TestSprint6SharingAndQr(Sprint6Fixture):
    def test_password_share_round_trip(self):
        service = SharingService(self.entry_manager)
        share = service.share_entry(self.entry_id, "alice", password="share-pass")

        result = service.import_shared_entry(share["package"], password="share-pass", save_to_vault=False)

        self.assertFalse(result["saved"])
        self.assertEqual(result["entry"]["title"], "GitHub")

    def test_rsa_public_key_export(self):
        keys = KeyExchangeService().generate_rsa_key_pair()
        exporter = VaultExporter(self.entry_manager)
        package = exporter.export_vault(public_key=keys["public_key"].encode("ascii"))

        importer = VaultImporter(self.entry_manager)
        result = importer.import_data(package, private_key=keys["private_key"].encode("ascii"), mode="dry-run")

        self.assertEqual(result["total"], 1)

    def test_qr_chunk_round_trip(self):
        qr = QRCodeService()
        payload = qr.build_payload("public_key", {"key": "A" * 1024})
        chunks = qr.generate_qr_chunks(payload, chunk_size=128)

        restored = qr.decode_qr_chunks(chunks)

        self.assertIsNotNone(restored)
        self.assertEqual(restored["data"]["key"], "A" * 1024)


if __name__ == "__main__":
    unittest.main()
