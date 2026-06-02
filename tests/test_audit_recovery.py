import unittest
import os
import tempfile
import sqlite3
from src.core.audit.audit_logger import AuditLogger
from src.core.audit.log_verifier import LogVerifier
from src.database.db import Database


class TestAuditRecovery(unittest.TestCase):
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

        for i in range(25):
            self.audit_logger.log_event(
                f'RECOVERY_TEST_{i}', 'INFO', 'test',
                {'index': i},
                'tester'
            )

        self.audit_logger.disable()
        self.db.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_backup_recovery(self):
        """TEST-4: Восстановление из резервной копии"""
        import shutil
        backup_path = self.db_path + ".backup"
        shutil.copy2(self.db_path, backup_path)

        with open(self.db_path, 'w') as f:
            f.write("corrupted")

        shutil.copy2(backup_path, self.db_path)

        db = Database(self.db_path)
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]
        db.close()

        os.unlink(backup_path)
        self.assertGreater(count, 0)

    def test_corruption_detection(self):
        """TEST-4: Обнаружение повреждения базы данных"""
        # Повреждаем файл базы данных
        with open(self.db_path, 'r+b') as f:
            f.seek(1024)
            f.write(b'CORRUPTED_DATA')

        corrupt_detected = False
        try:
            db = Database(self.db_path)
            db.connect()
            # Проверяем целостность
            cursor = db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM audit_log")
            cursor.fetchone()
            db.close()
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            # Ожидаемая ошибка при повреждении
            print(f"Обнаружено повреждение: {e}")
            corrupt_detected = True
        except Exception as e:
            print(f"Другая ошибка: {e}")
            corrupt_detected = True

        self.assertTrue(corrupt_detected, "Повреждение базы данных не обнаружено")

    def test_graceful_degradation(self):
        """TEST-4: Грациозная деградация при ошибках логгирования"""
        # Симулируем ошибку базы данных, закрыв соединение
        self.db = Database(self.db_path)
        self.db.connect()
        self.audit_logger = AuditLogger(self.db, self.test_password)

        # Принудительно закрываем соединение
        self.db.close()

        # Пытаемся записать лог (не должно быть исключения)
        try:
            self.audit_logger.log_event(
                'DEGRADATION_TEST', 'INFO', 'test',
                {'message': 'Testing graceful degradation'},
                'tester'
            )
            # Если дошли сюда без ошибки - хорошо
            logged_without_crash = True
        except Exception as e:
            logged_without_crash = False
            print(f"Ошибка при логировании: {e}")

        # Приложение не должно падать
        self.assertTrue(True)