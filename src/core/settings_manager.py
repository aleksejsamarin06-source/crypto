from src.database.db import Database


class SettingsManager:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.db.connect()

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

    def close(self):
        self.db.close()