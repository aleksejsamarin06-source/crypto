import time
from threading import RLock
from src.core.security.memory_guard import SecureMemory


class KeyStorage:
    def __init__(self):
        self.encryption_key = None # хранение только в памяти, не на диске
        self.last_activity = 0
        self.is_unlocked = False
        self.lock = RLock()
        self.timeout = 3600 # - время для устаревания час
        self.memory_guard = SecureMemory()

    def store_key(self, key: bytes):
        """Сохранение ключа в памяти"""
        with self.lock:
            self._secure_clear()

            self.encryption_key = bytearray(key) # в оперативной памяти
            self.last_activity = time.time()
            self.is_unlocked = True

    def get_key(self) -> bytes:
        """Получение ключа из памяти"""
        with self.lock:
            if not self.is_unlocked: # CACHE-1 если ключ заблокирован
                return None
            # затирает ключ через час(cache-2)
            if time.time() - self.last_activity > self.timeout:
                self.clear()
                return None

            self.last_activity = time.time()
            return bytes(self.encryption_key)

    def clear(self):
        """Затирание ключа в памяти"""
        with self.lock:
            self._secure_clear() # CACHE-4 - затирает ключ
            self.is_unlocked = False

    def _secure_clear(self):
        """Безопасное затирание ключа"""
        if self.encryption_key:
            self.memory_guard.wipe_bytearray(self.encryption_key)
            self.encryption_key = None

    def update_activity(self):
        """Обновление времени активности"""
        with self.lock:
            if self.is_unlocked:
                self.last_activity = time.time()

    def is_locked(self) -> bool:
        """Проверка заблокировано ли хранилище"""
        with self.lock:
            if not self.is_unlocked:
                return True
            if time.time() - self.last_activity > self.timeout:
                self.clear() # CACHE-4 - авто-блокировка и затирание (при прошествии часа)
                return True
            return False
