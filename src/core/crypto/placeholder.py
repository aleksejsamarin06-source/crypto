from .abstract import EncryptionService


class AES256Placeholder(EncryptionService):
    def encrypt(self, data: bytes, key: bytes) -> bytes:
        result = bytearray()
        for i, byte in enumerate(data):
            result.append(byte ^ key[i % len(key)])
        return bytes(result)

    def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        result = bytearray()
        for i, byte in enumerate(ciphertext):
            result.append(byte ^ key[i % len(key)])
        return bytes(result)
