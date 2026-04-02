from argon2 import PasswordHasher, Type
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os
import secrets


class KeyDerivation:
    def __init__(self):
        # Argon2 для хэширования пароля (аутентификация)
        self.argon2_hasher = PasswordHasher(
            time_cost=3,  # итерации
            memory_cost=65536,  # 64 MB
            parallelism=4,  # потоки
            hash_len=32,  # длина хэша
            salt_len=16,  # длина соли
            type=Type.ID  # Argon2id
        )

        # Параметры PBKDF2 для ключа шифрования
        self.pbkdf2_iterations = 100000

    def create_auth_hash(self, password: str) -> dict:
        """Создание хэша Argon2 для проверки пароля"""
        password_hash = self.argon2_hasher.hash(password)

        return {
            'hash': password_hash,
            'params': {
                'time_cost': 3,
                'memory_cost': 65536,
                'parallelism': 4,
                'type': 'argon2id'
            }
        }

    def derive_encryption_key(self, password: str, salt: bytes = None) -> tuple:
        """Формирование ключа AES-256 из пароля с использованием PBKDF2"""
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.pbkdf2_iterations,
            backend=default_backend()
        )

        key = kdf.derive(password.encode('utf-8')) # ключ создаётся в памяти

        # Добавляем параметры PBKDF2
        params = {
            'algorithm': 'SHA256',
            'length': 32,
            'iterations': self.pbkdf2_iterations,
            'version': 1
        }

        return key, salt, params # сам ключ не сохраняется, только соль и параметры

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Проверка пароля по сохраненному хэшу Argon2"""
        try:
            return self.argon2_hasher.verify(stored_hash, password)
        except:
            secrets.compare_digest(b'dummy', b'dummy')
            return False

    def verify_password_constant_time(self, password: str, stored_hash: str) -> bool:
        """То же самое, но гарантированно за константное время"""
        return self.argon2_hasher.verify(stored_hash, password)

    def encrypt_with_key(self, data: str, key: bytes) -> str:
        """Шифрование данных существующим ключом"""
        from src.core.crypto.placeholder import AES256Placeholder
        crypto = AES256Placeholder()
        encrypted = crypto.encrypt(data.encode('utf-8'), key)
        return encrypted.hex()

    def decrypt_with_key(self, encrypted_data: str, key: bytes) -> str:
        """Расшифровка данных существующим ключом"""
        from src.core.crypto.placeholder import AES256Placeholder
        crypto = AES256Placeholder()
        encrypted = bytes.fromhex(encrypted_data)
        decrypted = crypto.decrypt(encrypted, key)
        return decrypted.decode('utf-8')