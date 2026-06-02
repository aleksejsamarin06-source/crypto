import unittest
import os
import tempfile
import time
from src.core.audit.audit_logger import AuditLogger
from src.core.audit.log_verifier import LogVerifier
from src.database.db import Database


class TestAuditPerformance(unittest.TestCase):
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

    def test_logging_performance(self):
        """TEST-2: змерение скорости логирования 10000 событий"""
        start = time.time()

        for i in range(10000):
            self.audit_logger.log_event(
                f'PERF_TEST_{i}', 'INFO', 'test',
                {'index': i},
                'tester'
            )

        elapsed = time.time() - start
        avg_time_ms = (elapsed / 10000) * 1000

        print(f"\nЛогирование 10000 событий: {elapsed:.2f} сек")
        print(f"Среднее время на запись: {avg_time_ms:.2f} мс")

        self.assertLess(avg_time_ms, 10)

    def test_verification_performance(self):
        """TEST-2: змерение скорости верификации 1000 записей"""
        for i in range(1000):
            self.audit_logger.log_event(
                f'VERIFY_TEST_{i}', 'INFO', 'test',
                {'index': i},
                'tester'
            )

        verifier = LogVerifier(self.db, self.test_password)

        start = time.time()
        result = verifier.verify_range(1, 1000)
        elapsed = time.time() - start

        print(f"\nВерификация 1000 записей: {elapsed:.3f} сек")
        self.assertLess(elapsed, 1.0)

    def test_filter_performance(self):
        """TEST-2: змерение скорости фильтрации 10000 записей"""
        for i in range(10000):
            self.audit_logger.log_event(
                f'FILTER_TEST_{i}', 'INFO', 'test',
                {'index': i, 'category': 'A' if i % 2 == 0 else 'B'},
                'tester'
            )

        cursor = self.db.conn.cursor()

        start = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log
            WHERE event_type LIKE 'FILTER_TEST_%'
        """)
        cursor.fetchone()
        elapsed = time.time() - start

        print(f"\nФильтрация 10000 записей: {elapsed * 1000:.2f} мс")
        self.assertLess(elapsed * 1000, 500)
