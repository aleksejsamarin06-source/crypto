import unittest
import os
import tempfile
import json
from src.core.audit.audit_logger import AuditLogger
from src.core.audit.log_formatters import LogFormatter
from src.database.db import Database


class TestAuditExport(unittest.TestCase):
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

        for i in range(10):
            self.audit_logger.log_event(
                f'EXPORT_TEST_{i}', 'INFO', 'test',
                {'index': i, 'test_data': f'value_{i}'},
                'tester'
            )

    def tearDown(self):
        self.audit_logger.disable()
        self.db.close()
        os.unlink(self.db_path)

    def test_export_json(self):
        """TEST-3: Экспорт в JSON"""
        export_path = tempfile.NamedTemporaryFile(suffix='.json', delete=False).name

        formatter = LogFormatter(self.db)
        formatter.export_json(export_path)

        self.assertTrue(os.path.exists(export_path))
        self.assertGreater(os.path.getsize(export_path), 0)

        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        os.unlink(export_path)

    def test_export_csv(self):
        """TEST-3: Экспорт в CSV"""
        export_path = tempfile.NamedTemporaryFile(suffix='.csv', delete=False).name

        formatter = LogFormatter(self.db)
        formatter.export_csv(export_path)

        self.assertTrue(os.path.exists(export_path))
        self.assertGreater(os.path.getsize(export_path), 0)

        os.unlink(export_path)