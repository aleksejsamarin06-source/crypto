class EncryptionService:
    def encrypt(self, data: bytes, key: bytes) -> bytes:
        raise NotImplementedError

    def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        raise NotImplementedError