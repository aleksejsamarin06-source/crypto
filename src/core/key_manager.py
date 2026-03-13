import os
import hashlib
import binascii
from src.core.crypto.placeholder import AES256Placeholder
import ctypes

class KeyManager:
    def __init__(self):
        self.crypto = AES256Placeholder()
        self.current_key = None

    def create_master_hash(self, password: str) -> str:
        """Создание хеша мастер-пароля для проверки"""
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return binascii.hexlify(salt + key).decode('utf-8')

    def verify_master_password(self, password: str, stored_hash: str) -> bool:
        """Проверка мастер-пароля"""
        stored = binascii.unhexlify(stored_hash.encode('utf-8'))
        salt = stored[:16]
        original_key = stored[16:]

        test_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return test_key == original_key

    def set_master_password(self, password: str):
        """Создание ключа из мастер-пароля (для шифрования записей)"""
        password_bytes = bytearray(password.encode('utf-8'))

        try:
            salt = os.urandom(16)
            self.current_key = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, 100000)
        finally:
            self.secure_zero(password_bytes)

    def encrypt_password(self, plain_password: str) -> str:
        """Шифрование пароля"""
        if not self.current_key:
            raise ValueError("Ключ не установлен")

        data = plain_password.encode('utf-8')
        encrypted = self.crypto.encrypt(data, self.current_key)
        return encrypted.hex()

    def decrypt_password(self, encrypted_hex: str) -> str:
        """Расшифровка пароля"""
        if not self.current_key:
            raise ValueError("Ключ не установлен")

        encrypted = bytes.fromhex(encrypted_hex)
        decrypted = self.crypto.decrypt(encrypted, self.current_key)
        return decrypted.decode('utf-8')

    def secure_zero(self, data):
        """Затирание данных в памяти"""
        if isinstance(data, bytearray):
            for i in range(len(data)):
                data[i] = 0
        elif isinstance(data, bytes):
            arr = bytearray(data)
            for i in range(len(arr)):
                arr[i] = 0
        elif isinstance(data, str):
            arr = bytearray(data.encode('utf-8'))
            for i in range(len(arr)):
                arr[i] = 0

    def set_encryption_key(self, key: bytes):
        """Установка ключа шифрования"""
        self.current_key = key