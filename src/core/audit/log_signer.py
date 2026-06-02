# src/core/audit/log_signer.py
import hashlib
import hmac
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature


class AuditLogSigner:
    def __init__(self, master_password: str = None):
        self.private_key = None
        self.public_key = None
        self.use_ed25519 = False
        self.hmac_key = None

        if master_password:
            self.init_signer(master_password)

    def init_signer(self, master_password: str):
        """Инициализация подписанта на основе мастер-пароля"""
        try:
            key_material = hashlib.pbkdf2_hmac(
                'sha256',
                master_password.encode('utf-8'),
                b"audit-signing-ed25519",
                100000,
                32
            )
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_material)
            self.public_key = self.private_key.public_key()
            self.use_ed25519 = True
        except Exception:
            self.hmac_key = hashlib.pbkdf2_hmac(
                'sha256',
                master_password.encode('utf-8'),
                b"audit-signing-hmac",
                100000,
                32
            )
            self.use_ed25519 = False

    def sign(self, data: bytes) -> bytes:
        """Подпись данных"""
        if self.use_ed25519 and self.private_key:
            return self.private_key.sign(data)
        elif self.hmac_key:
            return hmac.new(self.hmac_key, data, hashlib.sha256).digest()
        raise ValueError("Подписант не инициализирован")

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Проверка подписи"""
        if self.use_ed25519 and self.public_key:
            try:
                self.public_key.verify(signature, data)
                return True
            except InvalidSignature:
                return False
        elif self.hmac_key:
            expected = hmac.new(self.hmac_key, data, hashlib.sha256).digest()
            return hmac.compare_digest(signature, expected)
        return False

    def get_public_key_hex(self) -> str:
        if self.use_ed25519 and self.public_key:
            return self.public_key.public_bytes_raw().hex()
        return ""