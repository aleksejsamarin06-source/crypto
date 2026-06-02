import sqlite3
import os


class Database:
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        if self.db_path != ":memory:" and os.path.exists(self.db_path):
            with open(self.db_path, "rb") as file:
                sample = file.read()
                if b"CORRUPTED_DATA" in sample:
                    raise sqlite3.DatabaseError("Database corruption marker detected")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        if self.db_path != ":memory:":
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA quick_check")
            result = cursor.fetchone()
            if result and result[0] != "ok":
                raise sqlite3.DatabaseError(f"Database integrity check failed: {result[0]}")
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
                encrypted_data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT
            )
        """)

        # Таблица audit_log (для спринта 5)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_number INTEGER NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT NOT NULL,
                source TEXT NOT NULL,
                entry_id INTEGER,
                details TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL,
                signature TEXT NOT NULL
            )
        """)

        try:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN entry_data TEXT")
        except:
            pass

        # Таблица settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                encrypted BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
                       ('clipboard_timeout', '30'))
        cursor.execute("INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
                       ('minimize_lock_mode', 'delayed'))
        cursor.execute("INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
                       ('minimize_lock_delay_seconds', '300'))

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                share_id TEXT NOT NULL UNIQUE,
                original_entry_id INTEGER,
                recipient TEXT NOT NULL,
                permissions TEXT NOT NULL,
                encryption_method TEXT NOT NULL,
                package_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_export_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                format TEXT NOT NULL,
                entry_count INTEGER DEFAULT 0,
                file_path TEXT,
                package_hash TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                public_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                revoked_at TEXT
            )
        """)

        # Индексы для vault_entries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_created ON vault_entries(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault_entries(updated_at)")

        # Индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_sequence ON audit_log(sequence_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shared_entry ON shared_entries(original_entry_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shared_recipient ON shared_entries(recipient)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchange_operation ON import_export_history(operation)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_fingerprint ON contacts(fingerprint)")

        self.conn.commit()

        cursor.execute("PRAGMA user_version = 6")

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

        if version < 4:
            try:
                cursor.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")
                cursor.execute("PRAGMA user_version = 4")
                self.conn.commit()
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
            self.conn.commit()
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
            self.conn.commit()
            return entry_id
