import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.core.crypto.abstract import EncryptionService

class AESGCMEncryption(EncryptionService):
    """Реальная реализация AES-256-GCM шифрования"""

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        """
        Шифрует данные с AES-256-GCM.
        Возвращает: nonce (12 байт) + ciphertext + tag (16 байт)
        """
        if len(key) != 32:
            raise ValueError("Ключ должен быть 32 байта (AES-256)")

        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt(self, ciphertext_with_nonce: bytes, key: bytes) -> bytes:
        """
        Расшифровывает данные.
        Ожидает: nonce (12 байт) + ciphertext + tag (16 байт)
        """
        if len(key) != 32:
            raise ValueError("Ключ должен быть 32 байта (AES-256)")

        nonce = ciphertext_with_nonce[:12]
        ciphertext = ciphertext_with_nonce[12:]

        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_entry(self, data: dict, key: bytes) -> bytes:
        """Шифрует всю запись целиком как JSON"""
        nonce = os.urandom(12)
        plaintext = json.dumps(data).encode('utf-8')
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt_entry(self, encrypted_blob: bytes, key: bytes) -> dict:
        """Расшифровывает всю запись"""
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode('utf-8'))