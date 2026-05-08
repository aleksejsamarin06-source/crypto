import unittest
from src.core.clipboard.clipboard_service import ClipboardService


class TestClipboardMemory(unittest.TestCase):
    def test_password_not_in_plaintext(self):
        """TEST-3: Проверка что пароль не хранится в памяти в открытом виде"""
        service = ClipboardService(timeout=1)
        test_password = "SuperSecretPassword123!"

        service.copy(test_password, "password", 1)

        current_item = service.current_item
        self.assertIsNotNone(current_item)

        if current_item and current_item.data:
            self.assertNotIn(test_password, current_item.data)
            self.assertNotEqual(current_item.data, test_password)

    def test_obfuscation_works(self):
        """Проверка, что обфускация работает"""
        service = ClipboardService(timeout=1)
        test_password = "MySecretPass"

        service.copy(test_password, "password", 1)

        obfuscated = service.current_item.data
        self.assertNotEqual(obfuscated, test_password)
        self.assertTrue(len(obfuscated) > 0)