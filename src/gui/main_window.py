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
from PySide6.QtWidgets import QCheckBox, QDialog, QVBoxLayout, QDialogButtonBox, QLabel, QPushButton
from PySide6.QtWidgets import QSystemTrayIcon
from src.core.clipboard.clipboard_service import ClipboardService
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

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))  # иконка, если есть
        self.tray_icon.show()

        from src.core.clipboard.clipboard_service import ClipboardService

        self.clipboard_service = ClipboardService()
        self.notifications_enabled = True

        event_system.subscribe('ClipboardCopied', self.on_clipboard_copied)
        event_system.subscribe('ClipboardCleared', self.on_clipboard_cleared)
        event_system.subscribe('ClipboardSuspicious', self.on_clipboard_suspicious)
        event_system.subscribe('ClipboardWillClear', self.on_clipboard_will_clear)

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
        self.clipboard_service = ClipboardService()

        event_system.subscribe('ClipboardCopied', self.on_clipboard_copied)
        event_system.subscribe('ClipboardCleared', self.on_clipboard_cleared)

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
        self.status_bar.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.status_bar and event.type() == QEvent.MouseButtonDblClick:
            self.show_clipboard_preview()
            return True
        return super().eventFilter(obj, event)

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
        if not self.key_storage or self.key_storage.is_locked():
            if self.notifications_enabled:
                self.status_bar.showMessage("Хранилище заблокировано. Сначала разблокируйте.", 2000)
            return

        menu = QMenu()

        copy_username = menu.addAction("Копировать имя пользователя")
        copy_password = menu.addAction("Копировать пароль")
        copy_all = menu.addAction("Копировать всё (логин:пароль)")
        copy_url = menu.addAction("Копировать URL")
        menu.addSeparator()
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")

        action = menu.exec(self.table.viewport().mapToGlobal(position))

        selected = self.table.selectedIndexes()
        if not selected:
            return

        row = selected[0].row()
        entry_id = int(self.table.item(row, 0).text())
        entry = self.entries_data.get(entry_id, {})

        try:
            if action == copy_username:
                username = entry.get("username", "")
                if username:
                    self.clipboard_service.copy(username, "username", entry_id)
                    if self.notifications_enabled:
                        self.status_bar.showMessage(f"Логин скопирован: {username}", 2000)
                elif self.notifications_enabled:
                    self.status_bar.showMessage("Логин не задан", 2000)

            elif action == copy_password:
                password = entry.get("password", "")
                if password:
                    self.clipboard_service.copy(password, "password", entry_id)
                    if self.notifications_enabled:
                        self.status_bar.showMessage(f"Пароль скопирован", 2000)
                elif self.notifications_enabled:
                    self.status_bar.showMessage("Пароль не задан", 2000)

            elif action == copy_all:
                username = entry.get("username", "")
                password = entry.get("password", "")
                if username and password:
                    clipboard_text = f"{username}:{password}"
                    self.clipboard_service.copy(clipboard_text, "both", entry_id)
                    if self.notifications_enabled:
                        self.status_bar.showMessage(f"Скопировано: {clipboard_text[:20]}...", 2000)
                elif username:
                    self.clipboard_service.copy(username, "username", entry_id)
                    if self.notifications_enabled:
                        self.status_bar.showMessage(f"Скопирован логин: {username}", 2000)
                elif password:
                    self.clipboard_service.copy(password, "password", entry_id)
                    if self.notifications_enabled:
                        self.status_bar.showMessage(f"Скопирован пароль", 2000)
                elif self.notifications_enabled:
                    self.status_bar.showMessage("Нет данных для копирования", 2000)

            elif action == copy_url:
                url = entry.get("url", "")
                if url:
                    self.clipboard_service.copy(url, "url", entry_id)
                    if self.notifications_enabled:
                        self.status_bar.showMessage(f"URL скопирован: {url}", 2000)
                elif self.notifications_enabled:
                    self.status_bar.showMessage("URL не задан", 2000)

            elif action == edit_action:
                self.edit_entry()

            elif action == delete_action:
                self.delete_entry()
        except Exception as e:
            print(f"Ошибка в контекстном меню: {e}")
            if self.notifications_enabled:
                self.status_bar.showMessage(f"Ошибка: {e}", 3000)

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

                from src.core.clipboard.clipboard_service import ClipboardService
                from src.core.settings_manager import SettingsManager

                # Загружаем настройки
                settings = SettingsManager(file_path)
                saved_timeout = settings.get('clipboard_timeout', '30')
                self.notifications_enabled = settings.get_notification_enabled()
                settings.close()

                # Создаём сервис с загруженным таймаутом
                self.clipboard_service = ClipboardService(timeout=int(saved_timeout))
                print(f"Уведомления включены: {self.notifications_enabled}")

                from src.core.clipboard.clipboard_monitor import ClipboardMonitor
                self.clipboard_monitor = ClipboardMonitor(self.clipboard_service)
                self.clipboard_monitor.start_monitoring()

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
        from src.core.settings_manager import SettingsManager

        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки буфера обмена")
        dialog.resize(300, 200)
        layout = QVBoxLayout(dialog)

        info_label = QLabel(f"Текущий таймаут: {self.clipboard_service.auto_clear_timeout} сек")
        layout.addWidget(info_label)

        timeout_btn = QPushButton("Изменить таймаут")
        timeout_btn.clicked.connect(self.change_timeout_dialog)
        layout.addWidget(timeout_btn)

        layout.addSpacing(10)

        self.notifications_checkbox = QCheckBox("Показывать уведомления в статус-баре")
        self.notifications_checkbox.setChecked(self.notifications_enabled)
        layout.addWidget(self.notifications_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            self.notifications_enabled = self.notifications_checkbox.isChecked()
            # Сохраняем в БД
            settings = SettingsManager(self.current_db_path)
            settings.set_notification_enabled(self.notifications_enabled)
            settings.close()
            if self.notifications_enabled:
                self.status_bar.showMessage("Настройки сохранены", 2000)

    def change_timeout_dialog(self):
        from PySide6.QtWidgets import QInputDialog
        from src.core.settings_manager import SettingsManager

        current = self.clipboard_service.auto_clear_timeout
        new_timeout, ok = QInputDialog.getInt(
            self, "Таймаут автоочистки",
            "Введите время в секундах (5-300):\n0 = никогда",
            current, 5, 300
        )

        if ok and new_timeout != current:
            self.clipboard_service.set_auto_clear_timeout(new_timeout)
            settings = SettingsManager(self.current_db_path)
            settings.set('clipboard_timeout', str(new_timeout))
            settings.close()
            if self.notifications_enabled:
                self.status_bar.showMessage(f"Таймаут изменён на {new_timeout} секунд", 2000)

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

        # Очистка буфера обмена при блокировке
        if hasattr(self, 'clipboard_service'):
            self.clipboard_service.clear()

        if hasattr(self, 'clipboard_monitor'):
            self.clipboard_monitor.stop_monitoring()

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

    def on_clipboard_copied(self, data):
        if self.notifications_enabled:
            timeout = data.get('timeout', 30)
            self.status_bar.showMessage(f"Скопировано в буфер обмена (очистится через {timeout}с)", 3000)

        # Запускаем таймер обновления статуса
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self.update_clipboard_status)
        self.status_update_timer.start(1000)

        if self.notifications_enabled:
            self.tray_icon.showMessage("CryptoSafe", f"Скопирован {data.get('data_type')}", QSystemTrayIcon.Information,
                                       2000)

    def update_clipboard_status(self):
        remaining = self.clipboard_service.get_remaining_time()
        if remaining > 0:
            if self.notifications_enabled:
                self.status_bar.showMessage(f"Буфер обмена: очистится через {remaining} сек", 1000)
        else:
            self.status_update_timer.stop()

    def on_clipboard_cleared(self, data):
        """Срабатывает когда буфер очищен"""
        if self.notifications_enabled:
            self.status_bar.showMessage("Буфер обмена очищен", 2000)

    def on_clipboard_will_clear(self, data):
        if self.notifications_enabled:
            seconds = data.get('seconds', 5)
            self.status_bar.showMessage(f"Буфер обмена очистится через {seconds} сек", 4000)

    def on_clipboard_suspicious(self, data):
        self.status_bar.showMessage("ВНИМАНИЕ: Обнаружена подозрительная активность с буфером обмена!", 5000)

    def show_clipboard_preview(self):
        """Показ замаскированного содержимого буфера"""
        if not hasattr(self, 'clipboard_service'):
            self.status_bar.showMessage("Буфер обмена не инициализирован", 2000)
            return

        item = self.clipboard_service.current_item
        if not item:
            self.status_bar.showMessage("Буфер обмена пуст", 2000)
            return

        from PySide6.QtWidgets import QInputDialog, QMessageBox, QLineEdit

        data = item.data
        data_type = item.data_type

        # Маскируем содержимое
        if len(data) > 4:
            masked = data[:4] + "••••" + (data[-2:] if len(data) > 6 else "")
        else:
            masked = "••••••••"

        # Запрашиваем пароль
        password, ok = QInputDialog.getText(
            self, "Просмотр буфера обмена",
            f"Тип: {data_type}\nСодержимое (маскировано): {masked}\n\nВведите мастер-пароль для полного просмотра:",
            QLineEdit.Password
        )

        if ok and password:
            # Проверка мастер-пароля (упрощённо - если есть key_manager и база открыта)
            if hasattr(self, 'key_manager') and self.key_manager.current_key:
                QMessageBox.information(self, "Полное содержимое", f"{data_type}: {data}")
            else:
                QMessageBox.warning(self, "Ошибка", "Неверный пароль или хранилище не открыто")

        item = self.clipboard_service.current_item
        if not item:
            self.status_bar.showMessage("Буфер обмена пуст", 2000)
            return

        from PySide6.QtWidgets import QInputDialog, QMessageBox

        data = item.data
        if len(data) > 4:
            masked = data[:4] + "••••" + data[-2:] if len(data) > 6 else data[:4] + "••••"
        else:
            masked = "••••••••"

        password, ok = QInputDialog.getText(
            self, "Просмотр буфера обмена",
            f"Содержимое ({item.data_type}): {masked}\n\nВведите мастер-пароль для полного просмотра:",
            QLineEdit.Password
        )

        if ok and password:
            QMessageBox.information(self, "Полное содержимое", f"{item.data_type}: {data}")
