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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_type TEXT NOT NULL,
                key_data TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_key (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_title ON vault_entries(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_tags ON vault_entries(tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entry_id ON audit_log(entry_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")

        self.conn.commit()

        # Установка версии схемы для будущих миграций (DB-3)
        cursor.execute("PRAGMA user_version = 2")

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

    def migrate_if_needed(self):
        """Проверка и обновление схемы базы данных"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        cursor.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]

        if version < 2:
            try:
                cursor.execute("ALTER TABLE key_store ADD COLUMN version INTEGER DEFAULT 1")
            except:
                pass

            cursor.execute("PRAGMA user_version = 2")
            self.conn.commit()
            print("База данных обновлена до версии 2")

    def save_entry(self, entry_id, entry_data):
        """Сохранение записи в базу данных"""
        cursor = self.conn.cursor()

        if entry_id is None:
            cursor.execute("""
                INSERT INTO vault_entries (title, username, encrypted_password, url, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                entry_data["title"],
                entry_data["username"],
                entry_data["encrypted_password"],
                entry_data["url"],
                entry_data["notes"]
            ))
            self.conn.commit()  # важно!
            return cursor.lastrowid
        else:
            cursor.execute("""
                UPDATE vault_entries 
                SET title=?, username=?, encrypted_password=?, url=?, notes=?
                WHERE id=?
            """, (
                entry_data["title"],
                entry_data["username"],
                entry_data["encrypted_password"],
                entry_data["url"],
                entry_data["notes"],
                entry_id
            ))
            self.conn.commit()  # важно!
            return entry_id