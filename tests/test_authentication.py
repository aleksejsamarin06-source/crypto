import unittest
import os
import tempfile
import json
from src.core.crypto.authentication import Authentication
from src.core.crypto.key_derivation import KeyDerivation
from src.database.db import Database


class TestAuthentication(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = Database(self.db_path)
        self.db.connect()
        self.db.create_tables()

        self.kd = KeyDerivation()
        self.test_password = "TestPassword123!"
        self.auth_data = self.kd.create_auth_hash(self.test_password)
        self.enc_key, self.enc_salt, self.pbkdf2_params = self.kd.derive_encryption_key(self.test_password)

        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
            ('auth_hash', self.auth_data['hash'], 1)
        )
        cursor.execute(
            "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
            ('enc_salt', self.enc_salt.hex(), 1)
        )
        cursor.execute(
            "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
            ('argon2_params', json.dumps(self.auth_data['params']), 1)
        )
        cursor.execute(
            "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
            ('pbkdf2_params', json.dumps(self.pbkdf2_params), 1)
        )
        self.db.conn.commit()

        self.auth = Authentication(self.db)
        self.auth.failed_attempts = 0
        self.auth.last_failed_time = 0

    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)

    def test_successful_login(self):
        """Тест успешного входа"""
        result = self.auth.login(self.test_password)
        self.assertTrue(result)
        self.assertIsNotNone(self.auth.key_storage.get_key())

    def test_failed_login(self):
        """Тест неудачного входа"""
        result = self.auth.login("WrongPassword")
        self.assertFalse(result)
        self.assertEqual(self.auth.failed_attempts, 1)

    @unittest.skip("Временно пропущен")
    def test_attempts_delay(self):
        """TEST-3: Тест задержки при неудачных попытках"""
        pass

    def test_logout(self):
        """Тест выхода"""
        self.auth.login(self.test_password)
        self.auth.logout()
        self.assertIsNone(self.auth.key_storage.get_key())
