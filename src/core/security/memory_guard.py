import ctypes
import platform
from typing import Any


class SecureMemory:
    """Secure memory allocation, locking and wiping where supported."""

    def __init__(self):
        self.system = platform.system()
        self._setup_platform_functions()

    def _setup_platform_functions(self):
        self.kernel32 = None
        self.libc = None
        if self.system == "Windows":
            self.kernel32 = ctypes.windll.kernel32
        elif self.system in ("Linux", "Darwin"):
            self.libc = ctypes.CDLL(None)

    def allocate_secure(self, size: int) -> Any:
        buffer = (ctypes.c_ubyte * size)()
        self.lock_memory(buffer, size)
        return buffer

    def lock_memory(self, buffer: Any, size: int) -> bool:
        try:
            if self.kernel32:
                return bool(self.kernel32.VirtualLock(ctypes.byref(buffer), size))
            if self.libc:
                return self.libc.mlock(ctypes.byref(buffer), size) == 0
        except Exception:
            return False
        return False

    def unlock_memory(self, buffer: Any, size: int) -> bool:
        try:
            if self.kernel32:
                return bool(self.kernel32.VirtualUnlock(ctypes.byref(buffer), size))
            if self.libc:
                return self.libc.munlock(ctypes.byref(buffer), size) == 0
        except Exception:
            return False
        return False

    def secure_zero(self, buffer: Any, size: int):
        if not buffer or size <= 0:
            return
        try:
            if self.kernel32 and hasattr(self.kernel32, "RtlSecureZeroMemory"):
                self.kernel32.RtlSecureZeroMemory(ctypes.byref(buffer), size)
            else:
                ctypes.memset(buffer, 0, size)
        finally:
            ctypes.memset(buffer, 0, size)

    def wipe_bytearray(self, data: bytearray):
        if data is None:
            return
        for index in range(len(data)):
            data[index] = 0

    def wipe_bytes_copy(self, data: bytes):
        if data is None:
            return
        copy = bytearray(data)
        self.wipe_bytearray(copy)

    def free_secure(self, buffer: Any, size: int):
        self.secure_zero(buffer, size)
        self.unlock_memory(buffer, size)


class SecretHolder:
    """Pinned memory holder for sensitive byte data."""

    def __init__(self, data: bytes):
        self._memory = SecureMemory()
        self._size = len(data)
        self._buffer = self._memory.allocate_secure(self._size)
        ctypes.memmove(self._buffer, data, self._size)

    def get_data(self) -> bytes:
        return bytes(self._buffer[:self._size])

    def wipe(self):
        if getattr(self, "_buffer", None):
            self._memory.free_secure(self._buffer, self._size)
            self._buffer = None

    def __del__(self):
        self.wipe()
