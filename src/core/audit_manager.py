from src.core.events import event_system
import datetime


class AuditManager:
    def __init__(self):
        self.logs = []  # временное хранение в памяти
        self.setup_subscriptions()

    def setup_subscriptions(self):
        event_system.subscribe("entry_added", self.log_entry_added)
        event_system.subscribe("entry_updated", self.log_entry_updated)
        event_system.subscribe("entry_deleted", self.log_entry_deleted)
        event_system.subscribe("user_logged_in", self.log_user_login)
        event_system.subscribe("user_logged_out", self.log_user_logout)

    def log_entry_added(self, data):
        self.add_log("Добавление", data)

    def log_entry_updated(self, data):
        self.add_log("Изменение", data)

    def log_entry_deleted(self, data):
        self.add_log("Удаление", data)

    def log_user_login(self, data):
        self.add_log("Вход в систему", data)

    def log_user_logout(self, data):
        self.add_log("Выход из системы", data)

    def add_log(self, action, data):
        log_entry = {
            "timestamp": datetime.datetime.now(),
            "action": action,
            "entry_id": data.get("id"),
            "entry_title": data.get("title", ""),
            "details": data.get("details", "")
        }
        self.logs.append(log_entry)
        print(f"Журнал: {action} - {data.get('title', '')}")  # отладка

    def get_logs(self):
        return self.logs.copy()
