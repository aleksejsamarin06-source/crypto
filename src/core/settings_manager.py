from src.database.db import Database


class SettingsManager:
    MINIMIZE_LOCK_MODES = ('disabled', 'immediate', 'delayed')
    SECURITY_PROFILES = ('standard', 'enhanced', 'paranoid')
    ACTIVITY_SENSITIVITY = ('low', 'medium', 'high')
    APP_THEMES = ('system', 'light', 'dark')

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

    def get_security_profile(self) -> str:
        profile = self.get('security_profile', 'standard')
        return profile if profile in self.SECURITY_PROFILES else 'standard'

    def set_security_profile(self, profile: str):
        if profile not in self.SECURITY_PROFILES:
            profile = 'standard'
        self.set('security_profile', profile)
        self.apply_security_profile(profile)

    def apply_security_profile(self, profile: str):
        profiles = {
            'standard': {
                'auto_lock_timeout_seconds': 300,
                'activity_sensitivity': 'medium',
                'side_channel_protection_enabled': 'true',
                'panic_close_app': 'false',
            },
            'enhanced': {
                'auto_lock_timeout_seconds': 180,
                'activity_sensitivity': 'high',
                'side_channel_protection_enabled': 'true',
                'panic_close_app': 'false',
            },
            'paranoid': {
                'auto_lock_timeout_seconds': 60,
                'activity_sensitivity': 'high',
                'side_channel_protection_enabled': 'true',
                'panic_close_app': 'true',
            },
        }
        for key, value in profiles.get(profile, profiles['standard']).items():
            self.set(key, str(value).lower() if isinstance(value, bool) else str(value))

    def get_auto_lock_timeout_seconds(self) -> int:
        try:
            timeout = int(self.get('auto_lock_timeout_seconds', '300'))
        except (TypeError, ValueError):
            timeout = 300
        return min(max(timeout, 60), 8 * 60 * 60)

    def set_auto_lock_timeout_seconds(self, timeout_seconds: int):
        timeout_seconds = min(max(int(timeout_seconds), 60), 8 * 60 * 60)
        self.set('auto_lock_timeout_seconds', str(timeout_seconds))

    def get_activity_sensitivity(self) -> str:
        sensitivity = self.get('activity_sensitivity', 'medium')
        return sensitivity if sensitivity in self.ACTIVITY_SENSITIVITY else 'medium'

    def set_activity_sensitivity(self, sensitivity: str):
        if sensitivity not in self.ACTIVITY_SENSITIVITY:
            sensitivity = 'medium'
        self.set('activity_sensitivity', sensitivity)

    def get_app_theme(self) -> str:
        theme = self.get('app_theme', 'dark')
        return theme if theme in self.APP_THEMES else 'dark'

    def set_app_theme(self, theme: str):
        if theme not in self.APP_THEMES:
            theme = 'dark'
        self.set('app_theme', theme)

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, str(default).lower()) == 'true'

    def set_bool(self, key: str, value: bool):
        self.set(key, str(bool(value)).lower())

    def validate_security_settings(self) -> list[str]:
        warnings = []
        if self.get_auto_lock_timeout_seconds() > 3600:
            warnings.append('Таймаут автоблокировки больше 1 часа снижает безопасность')
        if not self.get_bool('side_channel_protection_enabled', True):
            warnings.append('Защита от side-channel атак отключена')
        if self.get_minimize_lock_mode() == 'disabled':
            warnings.append('Блокировка при сворачивании отключена')
        return warnings

    def close(self):
        self.db.close()
