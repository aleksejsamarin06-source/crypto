import unittest
import os
from src.core.crypto.key_derivation import KeyDerivation


class TestKeyDerivation(unittest.TestCase):
    def setUp(self):
        self.kd = KeyDerivation()
        self.test_password = "TestPassword123!"

    def test_create_auth_hash(self):
        """TEST-1: Тест создания хэша Argon2"""
        result = self.kd.create_auth_hash(self.test_password)
        self.assertIn('hash', result)
        self.assertIn('params', result)
        self.assertTrue(len(result['hash']) > 0)

    def test_verify_password(self):
        """TEST-1: Тест проверки пароля"""
        result = self.kd.create_auth_hash(self.test_password)
        self.assertTrue(self.kd.verify_password(self.test_password, result['hash']))
        self.assertFalse(self.kd.verify_password("WrongPassword", result['hash']))

    def test_derive_encryption_key_consistency(self):
        """TEST-2: Тест консистентности ключей (100 раз одинаково)"""
        salt = os.urandom(16)
        first_key, _, _ = self.kd.derive_encryption_key(self.test_password, salt)

        for i in range(100):
            key, _, _ = self.kd.derive_encryption_key(self.test_password, salt)
            self.assertEqual(first_key, key, f"Ключ отличается на итерации {i}")

    def test_encrypt_decrypt_with_key(self):
        """Тест шифрования/расшифровки с ключом"""
        key, salt, _ = self.kd.derive_encryption_key(self.test_password)
        test_data = "Секретные данные"

        encrypted = self.kd.encrypt_with_key(test_data, key)
        decrypted = self.kd.decrypt_with_key(encrypted, key)

        self.assertEqual(test_data, decrypted)
