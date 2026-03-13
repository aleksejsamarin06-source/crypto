from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import KeyStorage
from src.core.key_manager import KeyManager
from src.core.events import event_system
from src.core.audit_manager import AuditManager
from src.gui.widgets.audit_log_dialog import AuditLogDialog
from src.gui.widgets.login_dialog import LoginDialog
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit
from src.database.db import Database
from src.database.backup import BackupManager
from src.gui.widgets.setup_wizard import SetupWizard
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                               QTableWidget, QTableWidgetItem, QStatusBar,
                               QMenuBar, QMenu, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt, QTimer
from src.gui.widgets.entry_dialog import EntryDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CryptoSafe Manager")
        self.resize(800, 600)

        self.entries_data = {}
        self.audit_manager = AuditManager()
        self.key_manager = KeyManager()
        self.key_storage = None
        self.current_db_path = None

        self.setup_menu()
        self.setup_table()
        self.setup_statusbar()

        self.check_first_run()

        self.inactivity_timer = QTimer()
        self.inactivity_timer.setInterval(60000)  # проверка каждую минуту
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start()

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Новый", self.run_setup_wizard)
        file_menu.addAction("Открыть", self.open_file)
        file_menu.addSeparator()
        file_menu.addAction("Резервная копия", self.backup)
        file_menu.addAction("Сменить пароль", self.change_password)
        file_menu.addSeparator()
        file_menu.addAction("Заблокировать", self.lock_vault)
        file_menu.addAction("Выход", self.close)

        edit_menu = menubar.addMenu("Правка")
        edit_menu.addAction("Добавить", self.add_entry)
        edit_menu.addAction("Редактировать", self.edit_entry)
        edit_menu.addAction("Удалить", self.delete_entry)

        view_menu = menubar.addMenu("Вид")
        view_menu.addAction("Журнал", self.show_logs)
        view_menu.addAction("Настройки", self.show_settings)

        help_menu = menubar.addMenu("Справка")
        help_menu.addAction("О программе", self.about)

    def setup_table(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Имя пользователя", "URL"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        layout.addWidget(self.table)

        self.load_placeholder_data()
        self.table.doubleClicked.connect(self.edit_entry)

    def setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Статус: Не авторизован | Готов к работе")

    def load_placeholder_data(self):
        self.table.setRowCount(0)

        for entry_id, data in self.entries_data.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(entry_id)))
            self.table.setItem(row, 1, QTableWidgetItem(data.get("title", "")))
            self.table.setItem(row, 2, QTableWidgetItem(data.get("username", "")))
            self.table.setItem(row, 3, QTableWidgetItem(data.get("url", "")))

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть базу данных",
            os.path.expanduser("~"),
            "Database files (*.db)"
        )

        if file_path:
            print(f"Открываем файл: {file_path}")

            db = Database(file_path)
            db.connect()

            login_dialog = LoginDialog(self, db)

            if login_dialog.exec():
                if hasattr(self, 'key_storage') and self.key_storage:
                    self.key_storage.update_activity()

                print("Вход выполнен успешно")

                encryption_key = login_dialog.encryption_key
                if encryption_key:
                    self.key_manager.set_encryption_key(encryption_key)
                    print("Ключ шифрования установлен")
                else:
                    print("ОШИБКА: ключ не получен")

                self.current_db_path = file_path
                print(f"Путь сохранён в self.current_db_path: {self.current_db_path}")

                cursor = db.conn.cursor()

                cursor.execute("SELECT id, title, username, encrypted_password, url, notes FROM vault_entries")
                rows = cursor.fetchall()
                print(f"Загружено записей из БД: {len(rows)}")

                self.entries_data = {}
                self.table.setRowCount(0)

                for row in rows:
                    entry_id = row[0]

                    self.entries_data[entry_id] = {
                        "title": row[1],
                        "username": row[2] or "",
                        "encrypted_password": row[3],
                        "url": row[4] or "",
                        "notes": row[5] or ""
                    }

                    row_pos = self.table.rowCount()
                    self.table.insertRow(row_pos)
                    self.table.setItem(row_pos, 0, QTableWidgetItem(str(entry_id)))
                    self.table.setItem(row_pos, 1, QTableWidgetItem(row[1]))
                    self.table.setItem(row_pos, 2, QTableWidgetItem(row[2] or ""))
                    self.table.setItem(row_pos, 3, QTableWidgetItem(row[4] or ""))

                db.close()
                print("База данных закрыта")

                self.status_bar.showMessage(
                    f"Статус: Открыта база {os.path.basename(file_path)} | Загружено {len(rows)} записей"
                )
            else:
                print("Вход отменён")
                db.close()

    def backup(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите базу данных для резервного копирования",
            os.path.expanduser("~"),
            "Database files (*.db)"
        )
        if file_path:
            backup_manager = BackupManager()
            backup_path = backup_manager.create_backup(file_path)
            if backup_path:
                QMessageBox.information(
                    self, "Резервная копия",
                    f"Создана резервная копия:\n{backup_path}"
                )
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать резервную копию")

    def add_entry(self):
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

        dialog = EntryDialog(self, "Добавить запись")
        result = dialog.show()

        if result:
            password = result["password"]
            encrypted_password = self.key_manager.encrypt_password(password)
            result["password"] = None

            print(f"Добавление записи: {result['title']}")  # отладка
            print(f"Путь к БД: {self.current_db_path}")  # отладка

            # Сохранение в базу данных
            if self.current_db_path and os.path.exists(self.current_db_path):
                try:
                    db = Database(self.current_db_path)
                    db.connect()
                    print("Подключились к БД")  # отладка

                    new_id = db.save_entry(None, {
                        "title": result["title"],
                        "username": result["username"],
                        "encrypted_password": encrypted_password,
                        "url": result["url"],
                        "notes": result["notes"]
                    })
                    print(f"Сохранено, ID: {new_id}")  # отладка

                    db.close()
                    print("БД закрыта")  # отладка
                except Exception as e:
                    print(f"Ошибка сохранения: {e}")  # отладка
                    QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {e}")
            else:
                print("Нет пути к БД или файл не существует")  # отладка
                new_id = len(self.entries_data) + 1

            self.entries_data[new_id] = {
                "title": result["title"],
                "username": result["username"],
                "encrypted_password": encrypted_password,
                "url": result["url"],
                "notes": result["notes"]
            }

            event_system.publish("entry_added", {
                "id": new_id,
                "title": result["title"],
                "details": f"Добавлена запись '{result['title']}'"
            })

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(new_id)))
            self.table.setItem(row, 1, QTableWidgetItem(result["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(result["username"]))
            self.table.setItem(row, 3, QTableWidgetItem(result["url"]))

            self.status_bar.showMessage(f"Статус: Запись '{result['title']}' добавлена")

    def edit_entry(self):
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "Информация", "Выберите запись для редактирования")
            return

        row = selected_rows[0].row()
        entry_id = int(self.table.item(row, 0).text())
        entry_data = self.entries_data.get(entry_id, {})

        dialog = EntryDialog(self, "Редактировать запись", entry_data)
        result = dialog.show()

        if result:
            encrypted_password = self.key_manager.encrypt_password(result["password"])

            if self.current_db_path:
                db = Database(self.current_db_path)
                db.connect()
                db.save_entry(entry_id, {
                    "title": result["title"],
                    "username": result["username"],
                    "encrypted_password": encrypted_password,
                    "url": result["url"],
                    "notes": result["notes"]
                })
                db.close()

            self.entries_data[entry_id] = {
                "title": result["title"],
                "username": result["username"],
                "encrypted_password": encrypted_password,
                "url": result["url"],
                "notes": result["notes"]
            }

            self.table.setItem(row, 1, QTableWidgetItem(result["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(result["username"]))
            self.table.setItem(row, 3, QTableWidgetItem(result["url"]))

            event_system.publish("entry_updated", {
                "id": entry_id,
                "title": result["title"],
                "details": f"Обновлена запись '{result['title']}'"
            })

            self.status_bar.showMessage(f"Статус: Запись '{result['title']}' обновлена")

    def delete_entry(self):
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "Информация", "Выберите запись для удаления")
            return

        row = selected_rows[0].row()
        entry_id = int(self.table.item(row, 0).text())
        title = self.table.item(row, 1).text()

        result = QMessageBox.question(
            self, "Подтверждение", "Удалить выбранную запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            if self.current_db_path:
                db = Database(self.current_db_path)
                db.connect()
                cursor = db.conn.cursor()
                cursor.execute("DELETE FROM vault_entries WHERE id=?", (entry_id,))
                db.conn.commit()
                db.close()

            event_system.publish("entry_deleted", {
                "id": entry_id,
                "title": title,
                "details": f"Удалена запись '{title}'"
            })

            if entry_id in self.entries_data:
                del self.entries_data[entry_id]

            self.table.removeRow(row)
            self.status_bar.showMessage(f"Статус: Запись '{title}' удалена")

    def show_logs(self):
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

        logs = self.audit_manager.get_logs()
        dialog = AuditLogDialog(self, logs)
        dialog.exec()

    def show_settings(self):
        QMessageBox.information(self, "Информация", "Настройки будут доступны в следующем спринте")

    def about(self):
        QMessageBox.information(
            self, "О программе",
            "CryptoSafe Manager\nВерсия: 0.1.0 (Sprint 1)\n\nМенеджер паролей с открытым кодом"
        )

    def check_first_run(self):
        result = QMessageBox.question(
            self, "Первый запуск",
            "Это первый запуск программы. Запустить мастер настройки?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.run_setup_wizard()

    def run_setup_wizard(self):
        wizard = SetupWizard(self)
        if wizard.exec():
            db_path = wizard.db_path
            master_password = wizard.master_password

            key_derivation = KeyDerivation()
            auth_data = key_derivation.create_auth_hash(master_password)

            enc_key, enc_salt, pbkdf2_params = key_derivation.derive_encryption_key(master_password)

            self.key_storage = KeyStorage()
            self.key_storage.store_key(enc_key)

            db = Database(db_path)
            db.connect()
            db.create_tables()

            cursor = db.conn.cursor()

            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('auth_hash', auth_data['hash'], 1)
            )

            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('enc_salt', enc_salt.hex(), 1)
            )

            import json
            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('argon2_params', json.dumps(auth_data['params']), 1)
            )

            cursor.execute(
                "INSERT INTO key_store (key_type, key_data, version) VALUES (?, ?, ?)",
                ('pbkdf2_params', json.dumps(pbkdf2_params), 1)
            )

            db.conn.commit()
            db.close()

            self.current_db_path = db_path
            self.entries_data = {}
            self.table.setRowCount(0)

            self.status_bar.showMessage(f"Статус: База создана {os.path.basename(db_path)}")

            QMessageBox.information(
                self, "Готово",
                "Хранилище успешно создано"
            )

    def lock_vault(self):
        if self.key_storage:
            self.key_storage.clear()

        self.entries_data = {}
        self.table.setRowCount(0)
        self.status_bar.showMessage("Статус: Хранилище заблокировано")

        if self.current_db_path:
            self.open_file()

    def check_inactivity(self):
        """Проверка неактивности и блокировка при необходимости"""
        if hasattr(self, 'key_storage') and self.key_storage:
            if self.key_storage.is_locked():
                self.lock_vault()

    def change_password(self):
        if not self.current_db_path:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте базу данных")
            return

        from src.gui.widgets.change_password_dialog import ChangePasswordDialog
        dialog = ChangePasswordDialog(self, self.current_db_path, self.key_manager.current_key)

        if dialog.exec():
            self.lock_vault()