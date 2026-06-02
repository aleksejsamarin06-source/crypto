import unittest
import os
import tempfile
from src.core.audit.audit_logger import AuditLogger
from src.database.db import Database


class TestAuditSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = Database(self.db_path)
        self.db.connect()
        self.db.create_tables()

        self.test_password = "TestMasterPassword123!"
        self.audit_logger = AuditLogger(self.db, self.test_password)
        self.audit_logger.enabled = True

    def tearDown(self):
        self.audit_logger.disable()
        self.db.close()
        os.unlink(self.db_path)

    def test_sql_injection_prevention(self):
        """TEST-5: Попытка SQL-инъекции через детали лога"""
        malicious_details = {
            'test': "1' OR '1'='1",
            'sql': "'; DROP TABLE audit_log; --"
        }

        try:
            self.audit_logger.log_event(
                'TEST', 'INFO', 'security',
                malicious_details,
                'tester'
            )
            success = True
        except Exception as e:
            success = False
            print(f"Ошибка: {e}")

        self.assertTrue(success)

        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        self.assertIsNotNone(cursor.fetchone())

    def test_append_only(self):
        """TEST-5: Проверка что логи только добавляются"""
        initial_count = self.db.conn.cursor().execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

        self.audit_logger.log_event('APPEND_TEST', 'INFO', 'test', {}, 'tester')

        new_count = self.db.conn.cursor().execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        self.assertEqual(new_count, initial_count + 1)