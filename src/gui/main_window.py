from src.core.crypto.key_derivation import KeyDerivation
from src.core.crypto.key_storage import KeyStorage
from src.core.key_manager import KeyManager
from src.core.events import event_system
from src.core.security.activity_monitor import ActivityMonitor
from src.core.security.panic_mode import PanicMode
from PySide6.QtGui import QAction, QKeySequence, QColor, QPainter, QPen
from src.core.audit_manager import AuditManager
from src.gui.widgets.audit_log_dialog import AuditLogDialog
from src.gui.widgets.login_dialog import LoginDialog
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit
from src.database.db import Database
from src.database.backup import BackupManager
from src.gui.widgets.setup_wizard import SetupWizard
import os
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QVBoxLayout,
                               QDialogButtonBox, QLabel, QPushButton, QSpinBox)
from PySide6.QtWidgets import QSystemTrayIcon
from src.core.clipboard.clipboard_service import ClipboardService
from PySide6.QtGui import QIcon, QPixmap, QShortcut
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTableWidget, QTableWidgetItem, QStatusBar,
                               QMenuBar, QMenu, QMessageBox, QHeaderView, QLabel)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QCoreApplication
from src.gui.widgets.entry_dialog import EntryDialog
from src.core.vault.entry_manager import EntryManager
from src.gui.theme_manager import ThemeManager
from enum import Enum


class VaultLockState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    PENDING_UNLOCK = "pending_unlock"
    PANIC = "panic"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.build_tray_icon("locked"))
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
        self.master_password = None
        self.minimize_lock_mode = 'delayed'
        self.minimize_lock_delay_seconds = 300
        self.security_profile = 'standard'
        self.auto_lock_timeout_seconds = 300
        self.activity_sensitivity = 'medium'
        self.minimize_to_tray = True
        self.start_minimized_to_tray = False
        self.panic_close_app = False
        self.panic_stealth_mode = False
        self.pending_auto_lock = False
        self.unlock_on_restore_pending = False
        self.unlock_dialog_open = False
        self.app_theme = 'dark'
        self.vault_state = VaultLockState.LOCKED
        self.internal_dialog_depth = 0
        self.force_quit_requested = False
        ThemeManager.apply(self.app_theme)
        self.panic_mode = PanicMode()
        self.panic_mode.register_handler(self.handle_panic_response)
        self.activity_monitor = ActivityMonitor(self.request_auto_lock, self.security_config())

        self.setup_menu()
        self.setup_security_shortcuts()
        self.setup_tray_menu()
        self.setup_table()
        self.setup_statusbar()
        self.clipboard_service = ClipboardService()

        event_system.subscribe('ClipboardCopied', self.on_clipboard_copied)
        event_system.subscribe('ClipboardCleared', self.on_clipboard_cleared)
        event_system.subscribe('log_tampering_detected', self.on_log_tampering)

        self.check_first_run()

        self.inactivity_timer = QTimer()
        self.inactivity_timer.setInterval(5000)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start()
        self.activity_monitor.start_monitoring()

        self.integrity_timer = QTimer()
        self.integrity_timer.setInterval(24 * 60 * 60 * 1000)  # 24 часа в миллисекундах
        self.integrity_timer.timeout.connect(self.check_log_integrity)
        self.integrity_timer.start()

        self.minimize_lock_timer = QTimer()
        self.minimize_lock_timer.setSingleShot(True)
        self.minimize_lock_timer.timeout.connect(self.lock_after_minimize_timeout)

        app = QCoreApplication.instance()
        if app:
            app.installEventFilter(self)
            app.applicationStateChanged.connect(self.on_application_state_changed)

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Новый", self.run_setup_wizard)
        file_menu.addAction("Открыть", lambda: self.open_file())
        file_menu.addSeparator()
        file_menu.addAction("Импорт", self.import_vault)
        file_menu.addAction("Экспорт", self.export_vault)
        file_menu.addAction("Принять запись", self.accept_shared_entry)
        file_menu.addSeparator()
        file_menu.addAction("Резервная копия", self.backup)
        file_menu.addAction("Сменить пароль", self.change_password)
        file_menu.addSeparator()
        file_menu.addAction("Заблокировать", lambda: self.lock_vault())
        file_menu.addAction("Выход", self.quit_application)

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

    def setup_security_shortcuts(self):
        self.panic_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        self.panic_shortcut.activated.connect(lambda: self.activate_panic_mode("hotkey"))

    def setup_tray_menu(self):
        tray_menu = QMenu(self)
        self.tray_status_action = tray_menu.addAction("Статус: заблокировано")
        self.tray_status_action.setEnabled(False)
        tray_menu.addSeparator()
        tray_menu.addAction("Показать окно", self.restore_from_tray)
        tray_menu.addAction("Заблокировать", lambda: self.lock_vault(reopen=False))
        tray_menu.addAction("Открыть/разблокировать", lambda: self.open_file())
        tray_menu.addAction("Быстрый поиск", self.quick_search)
        tray_menu.addAction("Очистить буфер обмена", self.clear_clipboard_from_tray)
        tray_menu.addSeparator()
        tray_menu.addAction("Panic mode", lambda: self.activate_panic_mode("tray"))
        tray_menu.addAction("Настройки", self.show_settings)
        tray_menu.addAction("Выход", self.quit_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.update_tray_state(False)

    def suspend_auto_lock(self):
        self.internal_dialog_depth += 1
        if hasattr(self, 'minimize_lock_timer') and self.minimize_lock_timer.isActive():
            self.minimize_lock_timer.stop()

    def resume_auto_lock(self):
        if self.internal_dialog_depth > 0:
            self.internal_dialog_depth -= 1
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

    def exec_internal_dialog(self, dialog):
        self.suspend_auto_lock()
        try:
            return dialog.exec()
        finally:
            self.resume_auto_lock()

    def quit_application(self):
        self.force_quit_requested = True
        if hasattr(self, 'minimize_lock_timer') and self.minimize_lock_timer.isActive():
            self.minimize_lock_timer.stop()
        if hasattr(self, 'activity_monitor') and self.activity_monitor:
            self.activity_monitor.stop_monitoring()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        QCoreApplication.quit()

    def security_config(self):
        return {
            "auto_lock_enabled": True,
            "auto_lock_timeout_seconds": self.auto_lock_timeout_seconds,
            "activity_sensitivity": self.activity_sensitivity,
        }

    def apply_security_settings(self):
        self.activity_monitor.update_config(self.security_config())
        if self.key_storage:
            self.key_storage.timeout = self.auto_lock_timeout_seconds

    def build_tray_icon(self, state: str) -> QIcon:
        colors = {
            "locked": QColor("#d18b00"),
            "unlocked": QColor("#22a447"),
            "panic": QColor("#c62828"),
        }
        color = colors.get(state, colors["locked"])
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#1f1f1f"), 3))
        painter.drawEllipse(8, 8, 48, 48)

        painter.setPen(QPen(QColor("white"), 5))
        painter.drawLine(23, 32, 30, 39)
        painter.drawLine(30, 39, 43, 25)
        painter.end()

        return QIcon(pixmap)

    def update_tray_state(self, unlocked: bool):
        self.tray_icon.setIcon(self.build_tray_icon("unlocked" if unlocked else "locked"))
        if hasattr(self, 'tray_status_action'):
            self.tray_status_action.setText("Статус: разблокировано" if unlocked else "Статус: заблокировано")
        tooltip = "CryptoSafe Manager - разблокировано" if unlocked else "CryptoSafe Manager - заблокировано"
        self.tray_icon.setToolTip(tooltip)

    def set_vault_state(self, state: VaultLockState):
        self.vault_state = state
        if state == VaultLockState.PANIC:
            self.tray_icon.setIcon(self.build_tray_icon("panic"))
            self.tray_icon.setToolTip("CryptoSafe Manager - PANIC MODE")
            if hasattr(self, 'tray_status_action'):
                self.tray_status_action.setText("Статус: PANIC MODE")
            return
        if state == VaultLockState.UNLOCKED:
            self.unlock_on_restore_pending = False
            self.update_tray_state(True)
            return
        if state == VaultLockState.LOCKED:
            self.unlock_on_restore_pending = False
        self.update_tray_state(False)

    def is_vault_unlocked(self) -> bool:
        return self.vault_state == VaultLockState.UNLOCKED and self.entry_manager is not None

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_from_tray()

    def restore_from_tray(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()
        self.record_user_activity()
        QTimer.singleShot(0, self.unlock_after_restore_if_needed)

    def quick_search(self):
        if not self.entries_data:
            QMessageBox.information(self, "Поиск", "Сначала откройте хранилище")
            return
        self.suspend_auto_lock()
        try:
            query, ok = QInputDialog.getText(self, "Быстрый поиск", "Введите название, логин, URL или категорию:")
        finally:
            self.resume_auto_lock()
        if not ok:
            return
        self.restore_from_tray()
        self.search_input.setText(query)

    def clear_clipboard_from_tray(self):
        if hasattr(self, 'clipboard_service'):
            self.clipboard_service.clear()
        self.status_bar.showMessage("Буфер обмена очищен", 2000)

    def request_auto_lock(self):
        self.pending_auto_lock = True

    def activate_panic_mode(self, method="manual"):
        self.panic_mode.activate(method)

    def handle_panic_response(self, method):
        self.set_vault_state(VaultLockState.PANIC)
        if hasattr(self, 'clipboard_service'):
            self.clipboard_service.clear()
        if self.key_storage:
            self.key_storage.clear()
        if self.key_manager:
            self.key_manager.current_key = None
        self.entries_data = {}
        self.table.setRowCount(0)
        event_system.publish('vault_locked', {'reason': 'panic', 'method': method})
        if hasattr(self, 'audit_logger'):
            try:
                self.audit_logger.log_event("PANIC_MODE_ACTIVATED", "CRITICAL", "panic_mode", {"method": method})
            except Exception as exc:
                print(f"Не удалось записать panic event: {exc}")
        if self.panic_stealth_mode:
            QMessageBox.critical(self, "Application Error", "Приложение столкнулось с ошибкой и будет скрыто.")
        self.hide()
        self.status_bar.showMessage("Panic mode: хранилище заблокировано")
        if self.panic_close_app:
            QCoreApplication.quit()

    def setup_table(self):
        central_widget = QWidget()
        central_widget.setMouseTracking(True)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)

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
        self.search_input.setMouseTracking(True)
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
        self.status_bar.setMouseTracking(True)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Статус: Не авторизован | Готов к работе")
        self.status_bar.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() in (
                QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                QEvent.MouseMove, QEvent.KeyPress, QEvent.FocusIn):
            self.record_user_activity()
        if obj == self.status_bar and event.type() == QEvent.MouseButtonDblClick:
            self.show_clipboard_preview()
            return True
        return super().eventFilter(obj, event)

    def record_user_activity(self):
        if hasattr(self, 'activity_monitor') and self.activity_monitor:
            self.activity_monitor.record_activity()
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.handle_window_minimized()
                if self.minimize_to_tray:
                    QTimer.singleShot(0, self.hide)
            else:
                self.cancel_minimize_lock()
                if self.isVisible():
                    QTimer.singleShot(0, self.unlock_after_restore_if_needed)

    def closeEvent(self, event):
        if hasattr(self, 'activity_monitor') and self.activity_monitor:
            self.activity_monitor.stop_monitoring()
        super().closeEvent(event)

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
        share_action = menu.addAction("Поделиться")
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")

        self.suspend_auto_lock()
        try:
            action = menu.exec(self.table.viewport().mapToGlobal(position))
        finally:
            self.resume_auto_lock()

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

            elif action == share_action:
                self.share_entry(entry_id)

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

    def open_file(self, file_path=None):
        if file_path is None:
            self.suspend_auto_lock()
            try:
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Открыть базу данных",
                    os.path.expanduser("~"),
                    "Database files (*.db)"
                )
            finally:
                self.resume_auto_lock()

        if file_path:
            print(f"Открываем файл: {file_path}")

            db = Database(file_path)
            db.connect()
            db.create_tables()

            login_dialog = LoginDialog(self, db)

            if self.exec_internal_dialog(login_dialog):
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

                from src.core.audit.audit_logger import AuditLogger
                master_password = login_dialog.master_password  # получаем пароль
                self.master_password = master_password
                self.audit_logger = AuditLogger(db, master_password)  # создаём логгер

                from src.core.audit.log_verifier import LogVerifier
                verifier = LogVerifier(db, master_password)
                integrity_result = verifier.check_integrity()

                if not integrity_result:
                    QMessageBox.warning(self, "Предупреждение", "Нарушена целостность журнала аудита!")

                from src.core.events import event_system
                event_system.publish('vault_unlocked', {'user_id': 'user'})

                self.entry_manager = EntryManager(db, self.key_manager)
                self.db = db

                from src.core.clipboard.clipboard_service import ClipboardService
                from src.core.settings_manager import SettingsManager

                # Загружаем настройки
                settings = SettingsManager(file_path)
                saved_timeout = settings.get('clipboard_timeout', '30')
                self.notifications_enabled = settings.get_notification_enabled()
                self.minimize_lock_mode = settings.get_minimize_lock_mode()
                self.minimize_lock_delay_seconds = settings.get_minimize_lock_delay_seconds()
                self.security_profile = settings.get_security_profile()
                self.auto_lock_timeout_seconds = settings.get_auto_lock_timeout_seconds()
                self.activity_sensitivity = settings.get_activity_sensitivity()
                self.minimize_to_tray = settings.get_bool('minimize_to_tray', True)
                self.start_minimized_to_tray = settings.get_bool('start_minimized_to_tray', False)
                self.panic_close_app = settings.get_bool('panic_close_app', False)
                self.panic_stealth_mode = settings.get_bool('panic_stealth_mode', False)
                self.app_theme = settings.get_app_theme()
                settings.close()
                ThemeManager.apply(self.app_theme)
                self.apply_security_settings()

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
                self.panic_mode.reset()
                self.set_vault_state(VaultLockState.UNLOCKED)
                if self.start_minimized_to_tray:
                    self.hide()
                return True
            else:
                print("Вход отменён")
                db.close()
                return False
        return False

    def backup(self):
        self.suspend_auto_lock()
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите базу данных для резервного копирования",
                os.path.expanduser("~"),
                "Database files (*.db)"
            )
        finally:
            self.resume_auto_lock()
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

    def export_vault(self):
        if not self.entry_manager or not self.master_password:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте хранилище")
            return
        from src.gui.widgets.export_dialog import ExportDialog
        dialog = ExportDialog(self, self.entry_manager, self.master_password)
        self.exec_internal_dialog(dialog)

    def import_vault(self):
        if not self.entry_manager:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте хранилище")
            return
        from src.gui.widgets.import_dialog import ImportDialog
        dialog = ImportDialog(self, self.entry_manager)
        if self.exec_internal_dialog(dialog):
            self.entries_data = {entry["id"]: entry for entry in self.entry_manager.get_all_entries()}
            self.load_placeholder_data()

    def share_entry(self, entry_id):
        if not self.entry_manager:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте хранилище")
            return
        from src.gui.widgets.share_dialog import ShareDialog
        dialog = ShareDialog(self, self.entry_manager, entry_id)
        self.exec_internal_dialog(dialog)

    def accept_shared_entry(self):
        if not self.entry_manager:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте хранилище")
            return

        self.suspend_auto_lock()
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите shared package",
                os.path.expanduser("~"),
                "JSON files (*.json);;All files (*)"
            )
        finally:
            self.resume_auto_lock()
        if not file_path:
            return

        try:
            import json
            with open(file_path, "r", encoding="utf-8") as file:
                package = json.load(file)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл:\n{exc}")
            return

        encryption_method = package.get("encryption", {}).get("method", "password")
        password = None
        private_key = None

        if encryption_method == "public_key":
            self.suspend_auto_lock()
            try:
                key_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Выберите приватный ключ",
                    os.path.expanduser("~"),
                    "PEM files (*.pem);;All files (*)"
                )
            finally:
                self.resume_auto_lock()
            if not key_path:
                return
            try:
                with open(key_path, "rb") as key_file:
                    private_key = key_file.read()
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка ключа", f"Не удалось прочитать приватный ключ:\n{exc}")
                return
        else:
            self.suspend_auto_lock()
            try:
                password, ok = QInputDialog.getText(
                    self,
                    "Пароль shared package",
                    "Введите пароль для принятия записи:",
                    QLineEdit.Password
                )
            finally:
                self.resume_auto_lock()
            if not ok or not password:
                return

        try:
            from src.core.import_export.sharing_service import SharingService

            service = SharingService(self.entry_manager)
            result = service.import_shared_entry(package, password=password, private_key=private_key)
            entry_id = result.get("entry_id")
            if entry_id:
                entry = self.entry_manager.get_entry(entry_id)
                self.entries_data[entry_id] = entry
            else:
                self.entries_data = {entry["id"]: entry for entry in self.entry_manager.get_all_entries()}
            self.load_placeholder_data()
            QMessageBox.information(self, "Готово", "Запись успешно принята")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка принятия записи", str(exc))

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
        dialog = AuditLogDialog(self, logs, self.current_db_path, self.master_password)
        dialog.entry_selected.connect(self.select_entry_by_id)
        self.exec_internal_dialog(dialog)

    def select_entry_by_id(self, entry_id):
        """Выбор записи в таблице по ID"""
        for row in range(self.table.rowCount()):
            if int(self.table.item(row, 0).text()) == entry_id:
                self.table.selectRow(row)
                self.table.scrollToItem(self.table.item(row, 0))
                break

    def show_settings(self):
        from src.core.settings_manager import SettingsManager

        if not self.current_db_path:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте базу данных")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки")
        dialog.resize(480, 680)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Буфер обмена"))
        info_label = QLabel(f"Текущий таймаут: {self.clipboard_service.auto_clear_timeout} сек")
        layout.addWidget(info_label)

        timeout_btn = QPushButton("Изменить таймаут")
        timeout_btn.clicked.connect(self.change_timeout_dialog)
        layout.addWidget(timeout_btn)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Блокировка при сворачивании"))
        self.minimize_lock_checkbox = QCheckBox("Закрывать хранилище при сворачивании окна")
        self.minimize_lock_checkbox.setChecked(self.minimize_lock_mode != 'disabled')
        layout.addWidget(self.minimize_lock_checkbox)

        self.minimize_lock_mode_combo = QComboBox()
        self.minimize_lock_mode_combo.addItem("Сразу", 'immediate')
        self.minimize_lock_mode_combo.addItem("Через заданное время", 'delayed')
        mode_index = 0 if self.minimize_lock_mode == 'immediate' else 1
        self.minimize_lock_mode_combo.setCurrentIndex(mode_index)
        layout.addWidget(self.minimize_lock_mode_combo)

        self.minimize_lock_delay_spin = QSpinBox()
        self.minimize_lock_delay_spin.setRange(1, 1440)
        self.minimize_lock_delay_spin.setSuffix(" мин")
        self.minimize_lock_delay_spin.setValue(max(1, self.minimize_lock_delay_seconds // 60))
        layout.addWidget(self.minimize_lock_delay_spin)

        def update_minimize_controls():
            enabled = self.minimize_lock_checkbox.isChecked()
            delayed = self.minimize_lock_mode_combo.currentData() == 'delayed'
            self.minimize_lock_mode_combo.setEnabled(enabled)
            self.minimize_lock_delay_spin.setEnabled(enabled and delayed)

        self.minimize_lock_checkbox.toggled.connect(update_minimize_controls)
        self.minimize_lock_mode_combo.currentIndexChanged.connect(update_minimize_controls)
        update_minimize_controls()

        layout.addSpacing(10)

        layout.addWidget(QLabel("Тема интерфейса"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Тёмная", 'dark')
        self.theme_combo.addItem("Светлая", 'light')
        self.theme_combo.addItem("Как в системе", 'system')
        theme_index = {'dark': 0, 'light': 1, 'system': 2}.get(self.app_theme, 0)
        self.theme_combo.setCurrentIndex(theme_index)
        layout.addWidget(self.theme_combo)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Профиль безопасности"))
        self.security_profile_combo = QComboBox()
        self.security_profile_combo.addItem("Standard - баланс безопасности и удобства", 'standard')
        self.security_profile_combo.addItem("Enhanced - усиленная защита", 'enhanced')
        self.security_profile_combo.addItem("Paranoid - максимальная защита", 'paranoid')
        profile_index = {'standard': 0, 'enhanced': 1, 'paranoid': 2}.get(self.security_profile, 0)
        self.security_profile_combo.setCurrentIndex(profile_index)
        layout.addWidget(self.security_profile_combo)
        self.security_profile_hint = QLabel("")
        layout.addWidget(self.security_profile_hint)

        self.auto_lock_spin = QSpinBox()
        self.auto_lock_spin.setRange(1, 8 * 60)
        self.auto_lock_spin.setSuffix(" мин")
        self.auto_lock_spin.setValue(max(1, self.auto_lock_timeout_seconds // 60))
        layout.addWidget(QLabel("Автоблокировка при неактивности"))
        layout.addWidget(self.auto_lock_spin)

        self.activity_sensitivity_combo = QComboBox()
        self.activity_sensitivity_combo.addItem("Низкая", 'low')
        self.activity_sensitivity_combo.addItem("Средняя", 'medium')
        self.activity_sensitivity_combo.addItem("Высокая", 'high')
        sensitivity_index = {'low': 0, 'medium': 1, 'high': 2}.get(self.activity_sensitivity, 1)
        self.activity_sensitivity_combo.setCurrentIndex(sensitivity_index)
        layout.addWidget(QLabel("Чувствительность активности"))
        layout.addWidget(self.activity_sensitivity_combo)

        def update_profile_hint(apply_defaults=True):
            profile = self.security_profile_combo.currentData()
            descriptions = {
                'standard': ("Standard: таймаут 5 минут, средняя чувствительность.", 5, 'medium'),
                'enhanced': ("Enhanced: таймаут 3 минуты, высокая чувствительность.", 3, 'high'),
                'paranoid': ("Paranoid: таймаут 1 минута, высокая чувствительность, panic close по умолчанию.", 1, 'high'),
            }
            text, minutes, sensitivity = descriptions.get(profile, descriptions['standard'])
            self.security_profile_hint.setText(text)
            if apply_defaults:
                self.auto_lock_spin.setValue(minutes)
                self.activity_sensitivity_combo.setCurrentIndex({'low': 0, 'medium': 1, 'high': 2}[sensitivity])
                self.panic_close_checkbox.setChecked(profile == 'paranoid')

        self.security_profile_combo.currentIndexChanged.connect(lambda: update_profile_hint(True))
        update_profile_hint(False)

        self.minimize_to_tray_checkbox = QCheckBox("Сворачивать в системный трей")
        self.minimize_to_tray_checkbox.setChecked(self.minimize_to_tray)
        layout.addWidget(self.minimize_to_tray_checkbox)

        self.start_minimized_checkbox = QCheckBox("После открытия хранилища скрывать окно в трей")
        self.start_minimized_checkbox.setChecked(self.start_minimized_to_tray)
        layout.addWidget(self.start_minimized_checkbox)

        self.panic_close_checkbox = QCheckBox("Panic mode закрывает приложение полностью")
        self.panic_close_checkbox.setChecked(self.panic_close_app)
        layout.addWidget(self.panic_close_checkbox)

        self.panic_stealth_checkbox = QCheckBox("Panic mode показывает системную ошибку")
        self.panic_stealth_checkbox.setChecked(self.panic_stealth_mode)
        layout.addWidget(self.panic_stealth_checkbox)

        layout.addSpacing(10)

        self.notifications_checkbox = QCheckBox("Показывать уведомления в статус-баре")
        self.notifications_checkbox.setChecked(self.notifications_enabled)
        layout.addWidget(self.notifications_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if self.exec_internal_dialog(dialog):
            self.notifications_enabled = self.notifications_checkbox.isChecked()
            if self.minimize_lock_checkbox.isChecked():
                self.minimize_lock_mode = self.minimize_lock_mode_combo.currentData()
            else:
                self.minimize_lock_mode = 'disabled'
            self.minimize_lock_delay_seconds = self.minimize_lock_delay_spin.value() * 60
            self.security_profile = self.security_profile_combo.currentData()
            self.auto_lock_timeout_seconds = self.auto_lock_spin.value() * 60
            self.activity_sensitivity = self.activity_sensitivity_combo.currentData()
            self.minimize_to_tray = self.minimize_to_tray_checkbox.isChecked()
            self.start_minimized_to_tray = self.start_minimized_checkbox.isChecked()
            self.panic_close_app = self.panic_close_checkbox.isChecked()
            self.panic_stealth_mode = self.panic_stealth_checkbox.isChecked()
            self.app_theme = self.theme_combo.currentData()

            settings = SettingsManager(self.current_db_path)
            settings.set_notification_enabled(self.notifications_enabled)
            settings.set_minimize_lock_mode(self.minimize_lock_mode)
            settings.set_minimize_lock_delay_seconds(self.minimize_lock_delay_seconds)
            settings.set_security_profile(self.security_profile)
            settings.set_auto_lock_timeout_seconds(self.auto_lock_timeout_seconds)
            settings.set_activity_sensitivity(self.activity_sensitivity)
            settings.set_bool('minimize_to_tray', self.minimize_to_tray)
            settings.set_bool('start_minimized_to_tray', self.start_minimized_to_tray)
            settings.set_bool('panic_close_app', self.panic_close_app)
            settings.set_bool('panic_stealth_mode', self.panic_stealth_mode)
            settings.set_app_theme(self.app_theme)
            warnings = settings.validate_security_settings()
            settings.close()
            ThemeManager.apply(self.app_theme)
            self.apply_security_settings()
            if self.notifications_enabled:
                message = "Настройки сохранены"
                if warnings:
                    message += f". Предупреждений: {len(warnings)}"
                self.status_bar.showMessage(message, 3000)

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
            "CryptoSafe Manager\n"
            "Версия: 0.8.0 (Sprint 8)\n"
            "Автор: aleksejsamarin06-source\n\n"
            "Локальный менеджер паролей с открытым кодом"
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
        if self.exec_internal_dialog(wizard):
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

            self.current_db_path = db_path
            self.master_password = master_password
            self.key_manager.set_encryption_key(enc_key)
            self.entry_manager = EntryManager(db, self.key_manager)
            self.db = db
            self.entries_data = {}
            self.table.setRowCount(0)
            self.set_vault_state(VaultLockState.UNLOCKED)

            from src.core.audit.audit_logger import AuditLogger
            self.audit_logger = AuditLogger(db, master_password)

            from src.core.clipboard.clipboard_monitor import ClipboardMonitor
            self.clipboard_monitor = ClipboardMonitor(self.clipboard_service)
            self.clipboard_monitor.start_monitoring()

            self.status_bar.showMessage(f"Статус: Открыта база {os.path.basename(db_path)} | Загружено 0 записей")

            QMessageBox.information(
                self, "Готово",
                "Хранилище создано и открыто"
            )

    def check_log_integrity(self):
        """Периодическая проверка целостности логов"""
        if hasattr(self, 'db') and self.db and hasattr(self, 'audit_logger'):
            from src.core.audit.log_verifier import LogVerifier
            try:
                verifier = LogVerifier(self.db, self.master_password)
                result = verifier.verify_range(0, 1000)  # проверяем последние 1000 записей
                if not result['is_valid']:
                    self.status_bar.showMessage("Нарушена целостность журнала аудита!", 5000)
            except Exception as e:
                print(f"Ошибка проверки целостности: {e}")

    def on_log_tampering(self, data):
        """Обработка обнаружения вмешательства в лог"""
        msg = "Обнаружено вмешательство в журнал аудита!\n\n"
        if data.get('invalid_signatures'):
            msg += f"Некорректные подписи в записях: {data['invalid_signatures']}\n"
        if data.get('chain_breaks'):
            msg += f"Разрывы хеш-цепочки: {data['chain_breaks']}\n"

        result = QMessageBox.critical(
            self,
            "КРИТИЧЕСКАЯ ОШИБКА",
            msg + "\n\nЗаблокировать хранилище?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.lock_vault()

    def lock_vault(self, reopen=True, pending_restore=False):
        if self.key_storage:
            self.key_storage.clear()
        if self.key_manager:
            self.key_manager.current_key = None

        # Очистка буфера обмена при блокировке
        if hasattr(self, 'clipboard_service'):
            self.clipboard_service.clear()

        if hasattr(self, 'clipboard_monitor'):
            self.clipboard_monitor.stop_monitoring()

        from src.core.events import event_system
        event_system.publish('vault_locked', {})

        self.entries_data = {}
        self.table.setRowCount(0)
        self.entry_manager = None
        self.master_password = None
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except Exception as e:
                print(f"Ошибка закрытия БД при блокировке: {e}")
            self.db = None
        self.status_bar.showMessage("Статус: Хранилище заблокировано")
        self.unlock_on_restore_pending = pending_restore
        self.set_vault_state(VaultLockState.PENDING_UNLOCK if pending_restore else VaultLockState.LOCKED)

        if reopen and self.current_db_path:
            self.open_file(self.current_db_path)

    def check_inactivity(self):
        """Проверка неактивности и блокировка при необходимости"""
        if self.vault_state != VaultLockState.UNLOCKED:
            return
        if hasattr(self, 'key_storage') and self.key_storage:
            if self.pending_auto_lock or self.activity_monitor.get_idle_time() >= self.auto_lock_timeout_seconds:
                self.pending_auto_lock = False
                self.lock_vault(reopen=False)
            elif self.key_storage.is_locked():
                self.lock_vault(reopen=False)

    def handle_window_minimized(self):
        if not self.current_db_path or not self.key_storage:
            return

        if self.minimize_lock_mode == 'disabled':
            print("Блокировка при сворачивании отключена")
            return

        if self.minimize_lock_mode == 'immediate':
            print("Окно свёрнуто - блокируем хранилище сразу")
            self.lock_vault(reopen=False, pending_restore=True)
            return

        self.minimize_lock_timer.start(self.minimize_lock_delay_seconds * 1000)
        print(f"Окно свёрнуто - блокировка через {self.minimize_lock_delay_seconds} сек")

    def cancel_minimize_lock(self):
        if hasattr(self, 'minimize_lock_timer') and self.minimize_lock_timer.isActive():
            self.minimize_lock_timer.stop()
            print("Отложенная блокировка при сворачивании отменена")
        if hasattr(self, 'key_storage') and self.key_storage:
            self.key_storage.update_activity()

    def lock_after_minimize_timeout(self):
        app = QCoreApplication.instance()
        app_inactive = app and app.applicationState() != Qt.ApplicationActive
        if (self.isMinimized() or app_inactive or not self.isVisible()) and self.minimize_lock_mode == 'delayed':
            print("Истёк таймаут блокировки - блокируем хранилище")
            if self.minimize_to_tray:
                self.hide()
            self.lock_vault(reopen=False, pending_restore=True)


    def unlock_after_restore_if_needed(self):
        if self.vault_state != VaultLockState.PENDING_UNLOCK and not self.unlock_on_restore_pending:
            return
        if self.unlock_dialog_open:
            return
        if not self.current_db_path:
            self.unlock_on_restore_pending = False
            return
        if self.isMinimized() or not self.isVisible():
            return
        if self.entry_manager is not None and self.master_password:
            self.unlock_on_restore_pending = False
            return

        self.unlock_dialog_open = True
        try:
            if self.open_file(self.current_db_path):
                self.unlock_on_restore_pending = False
        finally:
            self.unlock_dialog_open = False

    def handle_application_inactive(self):
        if self.force_quit_requested or self.internal_dialog_depth > 0:
            return
        if not self.current_db_path or not self.key_storage or not self.entry_manager:
            return
        if self.vault_state != VaultLockState.UNLOCKED:
            return
        if self.unlock_on_restore_pending or self.unlock_dialog_open:
            return
        if self.minimize_lock_mode == 'disabled':
            return

        if self.minimize_lock_mode == 'immediate':
            print("Приложение потеряло фокус - блокируем хранилище сразу")
            if self.minimize_to_tray:
                self.hide()
            self.lock_vault(reopen=False, pending_restore=True)
            return

        self.minimize_lock_timer.start(self.minimize_lock_delay_seconds * 1000)
        print(f"Приложение потеряло фокус - блокировка через {self.minimize_lock_delay_seconds} сек")

    def change_password(self):
        if not self.current_db_path:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте базу данных")
            return

        from src.gui.widgets.change_password_dialog import ChangePasswordDialog
        dialog = ChangePasswordDialog(self, self.current_db_path, self.key_manager.current_key)

        if self.exec_internal_dialog(dialog):
            self.lock_vault()

    def on_application_state_changed(self, state):
        """Событие изменения состояния приложения"""
        print(f"Состояние приложения изменилось: {state}")  # отладка

        if state == Qt.ApplicationInactive:
            print("Приложение стало неактивным")
            self.handle_application_inactive()
        elif state == Qt.ApplicationActive:
            self.cancel_minimize_lock()
            if self.isVisible():
                QTimer.singleShot(0, self.unlock_after_restore_if_needed)
        else:
            print(f"Другое состояние: {state}")

    def on_clipboard_copied(self, data):
        if self.notifications_enabled:
            timeout = data.get('timeout', 30)
            self.status_bar.showMessage(f"Скопировано в буфер обмена (очистится через {timeout}с)", 3000)

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
