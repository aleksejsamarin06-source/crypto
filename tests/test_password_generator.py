import unittest
from src.core.vault.password_generator import PasswordGenerator


class TestPasswordGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = PasswordGenerator()

    def test_generate_default(self):
        """Тест генерации пароля по умолчанию"""
        password = self.gen.generate()
        self.assertEqual(len(password), 16)

    def test_generate_custom_length(self):
        """Тест генерации с разной длиной"""
        for length in [8, 16, 32, 64]:
            password = self.gen.generate(length=length)
            self.assertEqual(len(password), length)

    def test_character_sets(self):
        """TEST-4: Проверка соответствия наборам символов"""
        # Только цифры
        password = self.gen.generate(length=20, uppercase=False, lowercase=False,
                                     digits=True, symbols=False)
        self.assertTrue(all(c.isdigit() for c in password))

        # Только заглавные
        password = self.gen.generate(length=20, uppercase=True, lowercase=False,
                                     digits=False, symbols=False)
        self.assertTrue(all(c.isupper() for c in password))

        # Только строчные
        password = self.gen.generate(length=20, uppercase=False, lowercase=True,
                                     digits=False, symbols=False)
        self.assertTrue(all(c.islower() for c in password))

    def test_no_duplicates_in_10000(self):
        """TEST-4: Генерация 10000 паролей без дубликатов"""
        passwords = set()
        for _ in range(10000):
            password = self.gen.generate(length=12)
            self.assertNotIn(password, passwords)
            passwords.add(password)

        # Вероятность дубликата при 10000 из 62^12 крайне мала
        self.assertEqual(len(passwords), 10000)

    def test_each_char_set_represented(self):
        """TEST-4: Проверка что есть хотя бы один символ из каждого набора"""
        password = self.gen.generate(length=20, uppercase=True, lowercase=True,
                                     digits=True, symbols=True)

        self.assertTrue(any(c.isupper() for c in password))
        self.assertTrue(any(c.islower() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
        self.assertTrue(any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password))