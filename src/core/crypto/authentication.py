import time
import json
from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import KeyStorage
from src.core.events import event_system


class Authentication:
    def __init__(self, db_connection):
        self.key_derivation = KeyDerivation()
        self.key_storage = KeyStorage()
        self.db = db_connection
        self.failed_attempts = 0
        self.last_failed_time = 0
        self.session_start = None

    def login(self, password: str) -> bool:
        """Вход в систему с проверкой пароля"""
        if not self._check_attempts():
            return False

        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT key_data FROM key_store WHERE key_type = 'auth_hash' ORDER BY version DESC LIMIT 1"
        )
        result = cursor.fetchone()

        if not result:
            return False

        stored_hash = result[0]

        if self.key_derivation.verify_password(password, stored_hash):
            self.failed_attempts = 0

            cursor.execute(
                "SELECT key_data FROM key_store WHERE key_type = 'enc_salt'"
            )
            salt_result = cursor.fetchone()

            cursor.execute(
                "SELECT key_data FROM key_store WHERE key_type = 'pbkdf2_params'"
            )
            params_result = cursor.fetchone()

            if params_result:
                params = json.loads(params_result[0])
                # Защита от DoS - ограничиваем параметры
                if params.get('iterations', 0) > 200000:  # максимум 200k итераций
                    params['iterations'] = 100000
                if params.get('memory_cost', 0) > 131072:  # максимум 128 MB
                    params['memory_cost'] = 65536

            if salt_result and params_result:
                salt = bytes.fromhex(salt_result[0]) if isinstance(salt_result[0], str) else salt_result[0]
                params = json.loads(params_result[0])
                key, _, _ = self.key_derivation.derive_encryption_key(password, salt)
                self.key_storage.store_key(key)

                self.session_start = time.time()

                event_system.publish("user_logged_in", {
                    "timestamp": self.session_start
                })

                return True

        self._register_failed_attempt()
        return False

    def logout(self):
        """Выход из системы"""
        self.key_storage.clear()
        self.session_start = None
        event_system.publish("user_logged_out", {
            "timestamp": time.time()
        })

    def _check_attempts(self) -> bool:
        """Проверка экспоненциальной задержки"""
        if self.failed_attempts == 0:
            return True

        time_since_last = time.time() - self.last_failed_time

        if self.failed_attempts >= 5:
            delay = 30
        elif self.failed_attempts >= 3:
            delay = 5
        else:
            delay = 1

        return time_since_last >= delay

    def _register_failed_attempt(self):
        """Регистрация неудачной попытки"""
        self.failed_attempts += 1
        self.last_failed_time = time.time()

    def get_session_info(self) -> dict:
        """Информация о текущей сессии"""
        return {
            "is_authenticated": not self.key_storage.is_locked(),
            "session_start": self.session_start,
            "last_activity": self.key_storage.last_activity,
            "inactive_seconds": time.time() - self.key_storage.last_activity if self.key_storage.last_activity else 0
        }

    def get_encryption_key(self):
        """Получение текущего ключа шифрования"""
        return self.key_storage.get_key()