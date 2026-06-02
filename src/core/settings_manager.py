from src.database.db import Database


class SettingsManager:
    MINIMIZE_LOCK_MODES = ('disabled', 'immediate', 'delayed')

    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.db.connect()
        self.db.create_tables()

    def get(self, key: str, default=None):
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return default

    def set(self, key: str, value: str):
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value)
        )
        self.db.conn.commit()

    def get_notification_enabled(self) -> bool:
        return self.get('notifications_enabled', 'true') == 'true'

    def set_notification_enabled(self, enabled: bool):
        self.set('notifications_enabled', str(enabled).lower())

    def get_minimize_lock_mode(self) -> str:
        mode = self.get('minimize_lock_mode', 'delayed')
        if mode not in self.MINIMIZE_LOCK_MODES:
            return 'delayed'
        return mode

    def set_minimize_lock_mode(self, mode: str):
        if mode not in self.MINIMIZE_LOCK_MODES:
            mode = 'delayed'
        self.set('minimize_lock_mode', mode)

    def get_minimize_lock_delay_seconds(self) -> int:
        try:
            delay = int(self.get('minimize_lock_delay_seconds', '300'))
        except (TypeError, ValueError):
            delay = 300
        return min(max(delay, 60), 86400)

    def set_minimize_lock_delay_seconds(self, delay_seconds: int):
        delay_seconds = min(max(int(delay_seconds), 60), 86400)
        self.set('minimize_lock_delay_seconds', str(delay_seconds))

    def close(self):
        self.db.close()
