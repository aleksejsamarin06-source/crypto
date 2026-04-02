import shutil
import datetime
import os

class BackupManager:
    def create_backup(self, db_path):
        # Создание копии с датой
        if os.path.exists(db_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{db_path}.backup_{timestamp}"
            shutil.copy2(db_path, backup_path)
            return backup_path
        return None
