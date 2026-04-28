import unittest
import os
from src.core.vault.encryption_service import AESGCMEncryption


class TestEncryptionService(unittest.TestCase):
    def setUp(self):
        self.crypto = AESGCMEncryption()
        self.key = os.urandom(32)  # 256 bit key
        self.test_data = {
            "title": "Test",
            "username": "user@test.com",
            "password": "secret123",
            "url": "https://test.com",
            "notes": "Test notes",
            "version": 1
        }

    def test_encrypt_decrypt_round_trip(self):
        """TEST-1: Тест цикла шифрования/расшифрования"""
        import json
        plaintext = json.dumps(self.test_data).encode('utf-8')

        encrypted = self.crypto.encrypt(plaintext, self.key)

        # Проверяем что encrypted не содержит открытый текст
        self.assertNotIn(b'Test', encrypted)
        self.assertNotIn(b'secret123', encrypted)

        decrypted = self.crypto.decrypt(encrypted, self.key)
        decrypted_data = json.loads(decrypted.decode('utf-8'))

        self.assertEqual(decrypted_data["title"], self.test_data["title"])
        self.assertEqual(decrypted_data["password"], self.test_data["password"])

    def test_encrypt_entry_method(self):
        """Тест encrypt_entry/decrypt_entry"""
        encrypted = self.crypto.encrypt_entry(self.test_data, self.key)
        decrypted = self.crypto.decrypt_entry(encrypted, self.key)

        self.assertEqual(decrypted["title"], self.test_data["title"])
        self.assertEqual(decrypted["username"], self.test_data["username"])