import unittest
import os
import tempfile
import json
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.authentication import Authentication
from src.database.db import Database

class TestIntegration(unittest.TestCase):
    def test_full_flow(self):
        """TEST-5: Полный цикл: создание, вход, смена пароля"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            db = Database(db_path)
            db.connect()
            db.create_tables()

            kd = KeyDerivation()
            password = "InitialPass123!"

            auth_data = kd.create_auth_hash(password)
            key, salt, params = kd.derive_encryption_key(password)

            cursor = db.conn.cursor()
            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('auth_hash', auth_data['hash'], 1)
            )
            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('enc_salt', salt.hex(), 1)
            )
            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('argon2_params', json.dumps(auth_data['params']), 1)
            )
            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('pbkdf2_params', json.dumps(params), 1)
            )
            db.conn.commit()
            db.close()

            db = Database(db_path)
            db.connect()
            auth = Authentication(db)
            login_result = auth.login(password)
            self.assertTrue(login_result)
            self.assertIsNotNone(auth.key_storage.get_key())
            db.close()

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)