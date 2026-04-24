import json
from datetime import datetime
from src.core.events import event_system
from src.core.vault.encryption_service import AESGCMEncryption


class EntryManager:
    def __init__(self, db_connection, key_manager):
        self.db = db_connection
        self.key_manager = key_manager
        self.crypto = AESGCMEncryption()

    def create_entry(self, data: dict) -> int:
        """Создание новой записи (шифруется вся запись)"""
        entry_data = {
            "title": data["title"],
            "username": data.get("username", ""),
            "password": data.get("password", ""),
            "url": data.get("url", ""),
            "domain": data.get("domain", ""),
            "notes": data.get("notes", ""),
            "category": data.get("category", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1
        }

        encrypted_blob = self.crypto.encrypt_entry(entry_data, self.key_manager.current_key)

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "INSERT INTO vault_entries (encrypted_data, created_at, updated_at) VALUES (?, ?, ?)",
                (encrypted_blob, datetime.now(), datetime.now())
            )
            self.db.conn.commit()
            entry_id = cursor.lastrowid
        except Exception as e:
            self.db.conn.rollback()
            raise e

        event_system.publish("entry_added", {"id": entry_id, "title": data["title"]})
        return entry_id

    def get_entry(self, entry_id: int) -> dict:
        """Получение записи по ID"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT encrypted_data FROM vault_entries WHERE id=?", (entry_id,))
        row = cursor.fetchone()

        if not row:
            return None

        encrypted_blob = row[0]
        entry_data = self.crypto.decrypt_entry(encrypted_blob, self.key_manager.current_key)
        entry_data["id"] = entry_id
        if "updated_at" not in entry_data:
            entry_data["updated_at"] = entry_data.get("created_at", "")
        return entry_data

    def get_all_entries(self) -> list:
        """Получение всех записей"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, encrypted_data FROM vault_entries")
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            entry_id = row[0]
            encrypted_blob = row[1]
            entry_data = self.crypto.decrypt_entry(encrypted_blob, self.key_manager.current_key)
            entry_data["id"] = entry_id
            if "updated_at" not in entry_data:
                entry_data["updated_at"] = entry_data.get("created_at", "")
            entries.append(entry_data)

        return entries

    def update_entry(self, entry_id: int, data: dict) -> bool:
        """Обновление записи"""
        entry_data = {
            "title": data["title"],
            "username": data.get("username", ""),
            "password": data.get("password", ""),
            "url": data.get("url", ""),
            "domain": data.get("domain", ""),
            "notes": data.get("notes", ""),
            "category": data.get("category", ""),
            "updated_at": datetime.now().isoformat(),
            "version": 2
        }

        encrypted_blob = self.crypto.encrypt_entry(entry_data, self.key_manager.current_key)

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "UPDATE vault_entries SET encrypted_data=?, updated_at=? WHERE id=?",
                (encrypted_blob, datetime.now(), entry_id)
            )
            self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise e

        event_system.publish("entry_updated", {"id": entry_id, "title": data["title"]})
        return True

    def delete_entry(self, entry_id: int) -> bool:
        """Удаление записи"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM vault_entries WHERE id=?", (entry_id,))
            self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise e

        event_system.publish("entry_deleted", {"id": entry_id})
        return True