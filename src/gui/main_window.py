from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import KeyStorage
from src.core.key_manager import KeyManager
from src.core.events import event_system
from PySide6.QtGui import QAction
from src.core.audit_manager import AuditManager
from src.gui.widgets.audit_log_dialog import AuditLogDialog
from src.gui.widgets.login_dialog import LoginDialog
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit
from src.database.db import Database
from src.database.backup import BackupManager
from src.gui.widgets.setup_wizard import SetupWizard
import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTableWidget, QTableWidgetItem, QStatusBar,
                               QMenuBar, QMenu, QMessageBox, QHeaderView, QLabel)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QCoreApplication
from src.gui.widgets.entry_dialog import EntryDialog
from src.core.vault.entry_manager import EntryManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CryptoSafe Manager")
        self.resize(800, 600)

        self.entries_data = {}
        self.audit_manager = AuditManager()
        self.key_manager = KeyManager()
        self.entry_manager = None
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

        app = QCoreApplication.instance()
        if app:
            app.applicationStateChanged.connect(self.on_application_state_changed)

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
        view_menu.addSeparator()

        self.show_passwords_action = QAction("Показать пароли", self)
        self.show_passwords_action.setCheckable(True)
        self.show_passwords_action.setShortcut("Ctrl+Shift+P")
        self.show_passwords_action.toggled.connect(self.toggle_passwords_visibility)
        view_menu.addAction(self.show_passwords_action)

        help_menu = menubar.addMenu("Справка")
        help_menu.addAction("О программе", self.about)

    def setup_table(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()

        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Название", "Логин", "Пароль", "URL", "Категория", "Изменено"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)

        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст для поиска...")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.load_placeholder_data()
        self.table.doubleClicked.connect(self.edit_entry)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

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

            username = data.get("username", "")
            if len(username) > 4:
                masked_username = username[:4] + "••••"
            else:
                masked_username = username + "••••"
            self.table.setItem(row, 2, QTableWidgetItem(masked_username))

            password = data.get("password", "")
            if hasattr(self, 'show_passwords_action') and self.show_passwords_action.isChecked():
                display_password = password
            else:
                display_password = "••••••••"
            self.table.setItem(row, 3, QTableWidgetItem(display_password))

            url = data.get("url", "")
            domain = url
            if "://" in url:
                domain = url.split("://")[1]
            if "/" in domain:
                domain = domain.split("/")[0]
            self.table.setItem(row, 4, QTableWidgetItem(domain))

            self.table.setItem(row, 5, QTableWidgetItem(data.get("category", "")))

            updated_at = data.get("updated_at", data.get("created_at", ""))
            if updated_at:
                updated_date = updated_at.split("T")[0]
            else:
                updated_date = ""
            self.table.setItem(row, 6, QTableWidgetItem(updated_date))

    def filter_table(self):
        """Фильтрация таблицы по поисковому запросу"""
        search_text = self.search_input.text().lower()

        for row in range(self.table.rowCount()):
            if not search_text:
                self.table.setRowHidden(row, False)
                continue

            entry_id = int(self.table.item(row, 0).text())
            data = self.entries_data.get(entry_id, {})

            title = data.get("title", "").lower()
            username = data.get("username", "").lower()
            url = data.get("url", "").lower()
            notes = data.get("notes", "").lower()
            category = data.get("category", "").lower()

            if (search_text in title or search_text in username or
                    search_text in url or search_text in notes or
                    search_text in category):
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)

    def show_context_menu(self, position):
        menu = QMenu()

        copy_username = menu.addAction("Копировать имя пользователя")
        copy_url = menu.addAction("Копировать URL")
        menu.addSeparator()
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")

        action = menu.exec(self.table.viewport().mapToGlobal(position))

        if action == copy_username:
            selected = self.table.selectedIndexes()
            if selected:
                row = selected[0].row()
                username = self.table.item(row, 2).text()
                QGuiApplication.clipboard().setText(username)
                self.status_bar.showMessage(f"Скопировано: {username}", 2000)

        elif action == copy_url:
            selected = self.table.selectedIndexes()
            if selected:
                row = selected[0].row()
                url = self.table.item(row, 3).text()
                QGuiApplication.clipboard().setText(url)
                self.status_bar.showMessage(f"Скопировано: {url}", 2000)

        elif action == edit_action:
            self.edit_entry()

        elif action == delete_action:
            self.delete_entry()

    def toggle_passwords_visibility(self, checked):
        """Глобальное переключение видимости паролей"""
        self.load_placeholder_data()
        self.status_bar.showMessage("Пароли " + ("показаны" if checked else "скрыты"), 2000)

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

                self.key_storage = KeyStorage()
                self.key_storage.store_key(encryption_key)

                print("Ключ шифрования установлен и сохранён в key_storage")

                self.entry_manager = EntryManager(db, self.key_manager)
                self.db = db

                entries = self.entry_manager.get_all_entries()
                self.entries_data = {entry["id"]: entry for entry in entries}
                self.load_placeholder_data()

                self.current_db_path = file_path
                print(f"Путь сохранён в self.current_db_path: {self.current_db_path}")

                self.status_bar.showMessage(
                    f"Статус: Открыта база {os.path.basename(file_path)} | Загружено {len(self.entries_data)} записей"
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
        dialog = EntryDialog(self, "Добавить запись")
        result = dialog.show()

        if result:
            entry_id = self.entry_manager.create_entry(result)
            entry = self.entry_manager.get_entry(entry_id)
            self.entries_data[entry_id] = entry
            self.load_placeholder_data()
            self.status_bar.showMessage(f"Запись '{result['title']}' добавлена")

    def edit_entry(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "Информация", "Выберите запись для редактирования")
            return

        row = selected_rows[0].row()
        entry_id = int(self.table.item(row, 0).text())
        entry_data = self.entry_manager.get_entry(entry_id)

        # Передаём entry_data в диалог, чтобы показать текущие значения
        dialog = EntryDialog(self, "Редактировать запись", entry_data)
        result = dialog.show()

        if result:
            self.entry_manager.update_entry(entry_id, result)
            updated = self.entry_manager.get_entry(entry_id)
            self.entries_data[entry_id] = updated
            self.load_placeholder_data()
            self.status_bar.showMessage(f"Запись '{result['title']}' обновлена")

    def delete_entry(self):
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
            self.entry_manager.delete_entry(entry_id)
            del self.entries_data[entry_id]
            self.load_placeholder_data()
            self.status_bar.showMessage(f"Запись '{title}' удалена")

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
            "CryptoSafe Manager\nВерсия: 0.3.0 (Sprint 3)\n\nМенеджер паролей с открытым кодом"
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

    def on_application_state_changed(self, state):
        """Событие изменения состояния приложения"""
        print(f"Состояние приложения изменилось: {state}")  # отладка

        if state == Qt.ApplicationInactive:
            print("Приложение стало неактивным - блокируем")
            if hasattr(self, 'key_storage') and self.key_storage:
                print("key_storage существует, очищаем")
                self.key_storage.clear()
                self.key_manager.current_key = None
                self.entries_data = {}
                self.table.setRowCount(0)
                self.status_bar.showMessage("Статус: Хранилище заблокировано")
            else:
                print("key_storage не существует")
        else:
            print(f"Другое состояние: {state}")
