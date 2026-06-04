import unittest
import os
import tempfile
import json
from src.core.audit.audit_logger import AuditLogger
from src.core.audit.log_verifier import LogVerifier
from src.database.db import Database


class TestAuditIntegrity(unittest.TestCase):
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

    def test_integrity_detection(self):
        """TEST-1: Создать 1000 записей, изменить одну, обнаружить нарушение"""
        # Создаём 1000 записей
        for i in range(1000):
            self.audit_logger.log_event(
                f'TEST_EVENT_{i}', 'INFO', 'test',
                {'index': i, 'data': f'test_data_{i}'},
                'tester'
            )

        # Проверяем что записи созданы
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1001)  # + genesis

        # Получаем ID записи для изменения
        cursor.execute("SELECT id, entry_data FROM audit_log WHERE sequence_number = 500")
        row = cursor.fetchone()
        entry_id = row[0]
        original_data = row[1]

        # Изменяем запись
        entry_data = json.loads(original_data)
        details = json.loads(entry_data['details'])
        details['data'] = 'TAMPERED_DATA'
        entry_data['details'] = json.dumps(details, ensure_ascii=False)
        modified_data = json.dumps(entry_data, sort_keys=True, ensure_ascii=False)
        cursor.execute("UPDATE audit_log SET entry_data = ? WHERE id = ?", (modified_data, entry_id))
        self.db.conn.commit()

        # Проверяем целостность
        verifier = LogVerifier(self.db, self.test_password)
        result = verifier.verify_full()

        # Должно быть обнаружено нарушение
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['invalid_signatures']), 0)
