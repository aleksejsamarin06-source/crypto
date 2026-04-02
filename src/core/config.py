class ConfigManager:
    def __init__(self):
        self.settings = {
            "db_path": "~/.cryptosafe/data.db",
            "encryption_enabled": True,
            "clipboard_timeout": 30,
            "auto_lock_minutes": 5
        }

    def get(self, key):
        return self.settings.get(key)

    def set(self, key, value):
        self.settings[key] = value
