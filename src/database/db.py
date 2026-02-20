import sqlite3
import os


class Database:
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        # Таблица vault_entries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                username TEXT,
                encrypted_password TEXT,
                url TEXT,
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица audit_log (для спринта 5)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                entry_id INTEGER,
                details TEXT,
                signature TEXT
            )
        """)

        # Таблица settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                encrypted BOOLEAN DEFAULT 0
            )
        """)

        # Таблица key_store (для спринта 2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_type TEXT NOT NULL,
                salt BLOB,
                hash BLOB,
                params TEXT
            )
        """)

        # Индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_title ON vault_entries(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_tags ON vault_entries(tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entry_id ON audit_log(entry_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")

        self.conn.commit()

        # Установка версии схемы для будущих миграций (DB-3)
        cursor.execute("PRAGMA user_version = 1")

        print("Таблицы успешно созданы")

    def insert_test_data(self):
        """Вставка тестовых данных для проверки"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        test_data = [
            ("Gmail", "user@gmail.com", "encrypted_pass_1", "https://gmail.com", "Основная почта", "почта,google"),
            ("GitHub", "devuser", "encrypted_pass_2", "https://github.com", "Репозитории", "код,dev"),
            ("Facebook", "john.doe", "encrypted_pass_3", "https://facebook.com", "Соцсеть", "соцсети")
        ]

        cursor.executemany("""
            INSERT INTO vault_entries (title, username, encrypted_password, url, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, test_data)

        self.conn.commit()
        print(f"Добавлено {len(test_data)} тестовых записей")