import unittest
import os
import tempfile
from src.core.vault.entry_manager import EntryManager
from src.core.vault.encryption_service import AESGCMEncryption
from src.database.db import Database
from src.core.key_manager import KeyManager


class TestEntryManager(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = Database(self.db_path)
        self.db.connect()
        self.db.create_tables()

        self.key_manager = KeyManager()
        # Создаём тестовый ключ
        self.test_key = os.urandom(32)
        self.key_manager.set_encryption_key(self.test_key)

        self.entry_manager = EntryManager(self.db, self.key_manager)

    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)

    def test_crud_100_entries(self):
        """TEST-2: CRUD с 100 записями"""
        # Создаём 100 записей
        entries_ids = []
        for i in range(100):
            entry_id = self.entry_manager.create_entry({
                "title": f"Test {i}",
                "username": f"user{i}@test.com",
                "password": f"pass{i}",
                "url": f"https://test{i}.com",
                "category": "test"
            })
            entries_ids.append(entry_id)

        self.assertEqual(len(entries_ids), 100)

        # Проверяем количество
        all_entries = self.entry_manager.get_all_entries()
        self.assertEqual(len(all_entries), 100)

        # Обновляем каждую вторую запись
        for i in range(0, 100, 2):
            self.entry_manager.update_entry(entries_ids[i], {
                "title": f"Updated {i}",
                "username": f"updated{i}@test.com",
                "password": f"newpass{i}",
                "url": f"https://updated{i}.com",
                "category": "updated"
            })

        # Удаляем каждую третью запись
        for i in range(0, 100, 3):
            self.entry_manager.delete_entry(entries_ids[i])

        # Проверяем оставшиеся записи
        remaining = self.entry_manager.get_all_entries()
        self.assertLess(len(remaining), 100)

        # Проверяем что удалённые записи недоступны
        for i in range(0, 100, 3):
            entry = self.entry_manager.get_entry(entries_ids[i])
            self.assertIsNone(entry)