import unittest
from src.core.crypto.key_storage import KeyStorage


class TestKeyStorage(unittest.TestCase):
    def setUp(self):
        self.storage = KeyStorage()
        self.test_key = b'x' * 32

    def test_store_and_get_key(self):
        """Тест сохранения и получения ключа"""
        self.storage.store_key(self.test_key)
        retrieved = self.storage.get_key()
        self.assertEqual(self.test_key, retrieved)

    def test_clear_key(self):
        """TEST-4: Тест затирания ключа"""
        self.storage.store_key(self.test_key)
        self.storage.clear()
        self.assertIsNone(self.storage.get_key())

    def test_timeout(self):
        """TEST-3: Тест таймаута"""
        storage = KeyStorage()
        storage.timeout = 1
        storage.store_key(b'test')

        self.assertFalse(storage.is_locked())
        self.assertIsNotNone(storage.get_key())
