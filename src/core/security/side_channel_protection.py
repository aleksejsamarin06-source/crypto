import hmac
import secrets
import time
from typing import Optional


class ConstantTimeOps:
    """Helpers for security-critical comparisons and bounded noise."""

    @staticmethod
    def compare_bytes(left: bytes, right: bytes) -> bool:
        return hmac.compare_digest(left or b"", right or b"")

    @staticmethod
    def compare_text(left: str, right: str) -> bool:
        return hmac.compare_digest((left or "").encode("utf-8"), (right or "").encode("utf-8"))

    @staticmethod
    def fixed_time_lookup(query: str, values: list[str]) -> Optional[str]:
        query_bytes = (query or "").encode("utf-8")
        found = None
        for value in values:
            if hmac.compare_digest(query_bytes, (value or "").encode("utf-8")):
                found = value
        return found

    @staticmethod
    def random_delay(max_milliseconds: int = 0):
        if max_milliseconds <= 0:
            return
        time.sleep(secrets.randbelow(max_milliseconds + 1) / 1000.0)


class SecurityHardening:
    """Configurable side-channel hardening facade."""

    def __init__(self, enabled: bool = True, random_delay_ms: int = 0):
        self.enabled = enabled
        self.random_delay_ms = random_delay_ms

    def compare_secret(self, left: str, right: str) -> bool:
        if self.enabled:
            ConstantTimeOps.random_delay(self.random_delay_ms)
            return ConstantTimeOps.compare_text(left, right)
        return left == right

    def compare_secret_bytes(self, left: bytes, right: bytes) -> bool:
        if self.enabled:
            ConstantTimeOps.random_delay(self.random_delay_ms)
            return ConstantTimeOps.compare_bytes(left, right)
        return left == right
