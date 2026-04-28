import unittest
import time
import os
import tempfile
from src.core.vault.entry_manager import EntryManager
from src.core.vault.password_generator import PasswordGenerator
from src.database.db import Database
from src.core.key_manager import KeyManager


class TestPerformance(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = Database(self.db_path)
        self.db.connect()
        self.db.create_tables()

        self.key_manager = KeyManager()
        self.test_key = os.urandom(32)
        self.key_manager.set_encryption_key(self.test_key)

        self.entry_manager = EntryManager(self.db, self.key_manager)
        self.gen = PasswordGenerator()

    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)

    def test_load_1000_entries_performance(self):
        """PERF-1: Загрузка 1000 записей < 2 секунд"""
        # Создаём 1000 записей
        for i in range(1000):
            self.entry_manager.create_entry({
                "title": f"Test {i}",
                "username": f"user{i}@test.com",
                "password": self.gen.generate(),
                "url": f"https://test{i}.com",
                "category": "test"
            })

        # Замеряем загрузку
        start = time.time()
        entries = self.entry_manager.get_all_entries()
        elapsed = time.time() - start

        print(f"\nЗагрузка 1000 записей: {elapsed:.3f} секунд")
        self.assertEqual(len(entries), 1000)
        self.assertLess(elapsed, 2.0, f"Загрузка заняла {elapsed:.3f}с, должно быть < 2с")

    def test_search_performance(self):
        """PERF-2: Поиск среди 1000 записей < 200 мс"""
        # Создаём 1000 записей
        for i in range(1000):
            self.entry_manager.create_entry({
                "title": f"SearchTest {i}",
                "username": f"user{i}@test.com",
                "password": self.gen.generate(),
                "url": f"https://test{i}.com",
                "notes": f"Note {i}",
                "category": "test"
            })

        # Загружаем в память (как в main_window)
        entries = self.entry_manager.get_all_entries()

        # Замеряем поиск
        search_text = "SearchTest 500"
        start = time.time()

        results = []
        for data in entries:
            if (search_text in data.get("title", "") or
                    search_text in data.get("username", "") or
                    search_text in data.get("notes", "")):
                results.append(data)

        elapsed = time.time() - start
        elapsed_ms = elapsed * 1000

        print(f"\nПоиск среди 1000 записей: {elapsed_ms:.2f} мс")
        self.assertGreater(len(results), 0)
        self.assertLess(elapsed_ms, 200, f"Поиск занял {elapsed_ms:.2f}мс, должно быть < 200мс")

    def test_memory_usage(self):
        """PERF-3: Использование памяти < 50 МБ для 1000 записей"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Создаём 1000 записей
        entries_data = {}
        for i in range(1000):
            data = {
                "title": f"Test {i}",
                "username": f"user{i}@test.com" * 5,  # увеличиваем размер
                "password": self.gen.generate(),
                "url": f"https://test{i}.com",
                "notes": f"Note {i}" * 10,
                "category": "test"
            }
            entries_data[i] = data

        memory_after = process.memory_info().rss / 1024 / 1024
        memory_used = memory_after - memory_before

        print(f"\nИспользование памяти для 1000 записей: {memory_used:.2f} МБ")
        self.assertLess(memory_used, 50, f"Памяти использовано {memory_used:.2f}МБ, должно быть < 50МБ")