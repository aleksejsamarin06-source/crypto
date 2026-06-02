import os

os.environ['UNITTEST_RUNNING'] = '1'

import unittest
import tempfile
from src.core.clipboard.clipboard_service import ClipboardService
from src.core.vault.entry_manager import EntryManager
from src.database.db import Database
from src.core.key_manager import KeyManager


class TestClipboardIntegration(unittest.TestCase):
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
        self.clipboard_service = ClipboardService(timeout=1)

    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)

    def test_copy_from_entry(self):
        entry_id = self.entry_manager.create_entry({
            "title": "Test",
            "username": "testuser",
            "password": "secretpass123",
            "url": "https://test.com"
        })

        entry = self.entry_manager.get_entry(entry_id)
        self.assertIsNotNone(entry)

        result = self.clipboard_service.copy(entry["password"], "password", entry_id)
        self.assertTrue(result)
        self.assertIsNotNone(self.clipboard_service.current_item)

    def test_clear_on_lock(self):
        self.clipboard_service.copy("secret", "password", 1)
        self.assertIsNotNone(self.clipboard_service.current_item)

        self.clipboard_service.clear()
        self.assertIsNone(self.clipboard_service.current_item)