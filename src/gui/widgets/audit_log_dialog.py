# src/gui/widgets/audit_log_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QPushButton,
                               QHBoxLayout, QLineEdit, QComboBox, QLabel,
                               QDateEdit, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt, QDate, Signal
from datetime import datetime
from src.core.audit.log_formatters import LogFormatter
from src.database.db import Database


class AuditLogDialog(QDialog):
    entry_selected = Signal(int)

    def __init__(self, parent=None, log_entries=None, db_path=None, master_password=None):
        super().__init__(parent)
        self.setWindowTitle("Журнал действий")
        self.resize(900, 600)
        self.setModal(True)

        self.master_password = master_password

        self.log_entries = log_entries or []
        self.db_path = db_path
        self.current_page = 0
        self.page_size = 50
        self.all_entries = []

        self.setup_ui()
        self.load_all_entries()
        self.apply_filters()
        self.load_page()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Панель фильтров
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Тип события:"))
        self.event_type_combo = QComboBox()
        self.event_type_combo.addItem("Все")
        self.event_type_combo.addItems(["AUTH_LOGIN_SUCCESS", "AUTH_LOGOUT",
                                        "VAULT_ENTRY_CREATED", "VAULT_ENTRY_UPDATED",
                                        "VAULT_ENTRY_DELETED", "CLIPBOARD_COPIED",
                                        "CLIPBOARD_CLEARED", "SETTINGS_CHANGED"])
        self.event_type_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.event_type_combo)

        filter_layout.addWidget(QLabel("Уровень:"))
        self.severity_combo = QComboBox()
        self.severity_combo.addItem("Все")
        self.severity_combo.addItems(["INFO", "WARN", "ERROR", "CRITICAL"])
        self.severity_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.severity_combo)

        filter_layout.addWidget(QLabel("Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по деталям...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.search_input)

        # Фильтр по дате
        filter_layout.addWidget(QLabel("С:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)

        # Фильтр по пользователю
        filter_layout.addWidget(QLabel("Пользователь:"))
        self.user_combo = QComboBox()
        self.user_combo.addItem("Все")
        self.user_combo.setEditable(True)
        self.user_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.user_combo)

        layout.addLayout(filter_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Время", "Тип события", "Уровень", "Пользователь", "Источник", "ID записи"])
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_item_double_click)
        layout.addWidget(self.table)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Панель пагинации
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Назад")
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn = QPushButton("Вперёд")
        self.next_btn.clicked.connect(self.next_page)
        self.page_label = QLabel("Страница 1")

        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)

        # Панель кнопок
        button_layout = QHBoxLayout()

        self.verify_btn = QPushButton("Проверить целостность")
        self.verify_btn.clicked.connect(self.verify_integrity)

        export_json_btn = QPushButton("Экспорт JSON")
        export_json_btn.clicked.connect(lambda: self.export_log('json'))
        export_csv_btn = QPushButton("Экспорт CSV")
        export_csv_btn.clicked.connect(lambda: self.export_log('csv'))

        button_layout.addWidget(self.verify_btn)
        button_layout.addWidget(export_json_btn)
        button_layout.addWidget(export_csv_btn)
        button_layout.addStretch()

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_all_entries(self):
        """Загрузка всех записей из БД через LogFormatter"""
        if self.db_path:
            db = Database(self.db_path)
            db.connect()
            formatter = LogFormatter(db)
            self.all_entries = formatter.get_all_entries()

            users = set()
            for entry in self.all_entries:
                user = entry.get('user_id', '')
                if user and user != 'system':
                    users.add(user)
            self.user_combo.clear()
            self.user_combo.addItem("Все")
            for user in sorted(users):
                self.user_combo.addItem(user)

            db.close()
        else:
            # Fallback на переданные записи
            self.all_entries = self.log_entries

    def on_filter_changed(self):
        self.current_page = 0
        self.apply_filters()
        self.load_page()

    def apply_filters(self):
        event_type = self.event_type_combo.currentText()
        severity = self.severity_combo.currentText()
        search_text = self.search_input.text().lower()

        date_from = self.date_from.date().toPython()
        date_to = self.date_to.date().toPython()

        self.filtered_entries = []
        for entry in self.all_entries:
            if event_type != "Все" and entry.get('event_type') != event_type:
                continue
            if severity != "Все" and entry.get('severity') != severity:
                continue
            if search_text:
                details = str(entry.get('details', '')).lower()
                if search_text not in details:
                    continue

            timestamp = entry.get('timestamp', '')
            if timestamp:
                try:
                    entry_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    if entry_date < date_from or entry_date > date_to:
                        continue
                except:
                    pass

            self.filtered_entries.append(entry)

    def load_page(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_entries = self.filtered_entries[start:end]

        self.table.setRowCount(len(page_entries))
        for row, entry in enumerate(page_entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.get('timestamp', '')[:19]))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get('event_type', '')))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get('severity', '')))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get('user_id', '')))
            self.table.setItem(row, 4, QTableWidgetItem(entry.get('source', '')))
            entry_id = str(entry.get('entry_id', ''))
            self.table.setItem(row, 5, QTableWidgetItem(entry_id))

        total_pages = max(1, (len(self.filtered_entries) + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled((self.current_page + 1) * self.page_size < len(self.filtered_entries))

    def show_context_menu(self, position):
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        goto_action = menu.addAction("Перейти к записи в хранилище")
        action = menu.exec(self.table.viewport().mapToGlobal(position))

        if action == goto_action:
            row = self.table.currentRow()
            if row >= 0 and row < len(self.filtered_entries):
                entry = self.filtered_entries[row]
                entry_id = entry.get('entry_id')
                if entry_id:
                    self.entry_selected.emit(entry_id)
                    self.accept()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_entries):
            self.current_page += 1
            self.load_page()

    def on_item_double_click(self, index):
        row = index.row()
        if row < len(self.filtered_entries):
            entry = self.filtered_entries[row]
            sequence = entry.get('sequence', row + 1)
            self.show_verification_details(entry, sequence)

    def show_entry_details(self, entry):
        """Показ деталей записи в отдельном диалоге"""
        from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Детали записи")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        import json
        text_edit.setText(json.dumps(entry, indent=2, ensure_ascii=False))
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def verify_integrity(self):
        from src.core.audit.log_verifier import LogVerifier
        from src.database.db import Database

        if not self.db_path:
            QMessageBox.warning(self, "Ошибка", "Путь к базе данных не указан")
            return

        db = Database(self.db_path)
        db.connect()

        verifier = LogVerifier(db, self.master_password)
        report = verifier.get_verification_report()

        db.close()

        QMessageBox.information(self, "Результат проверки целостности", report)

    def export_log(self, fmt):
        from PySide6.QtWidgets import QFileDialog
        from src.core.audit.log_formatters import LogFormatter
        from src.database.db import Database

        password, ok = QInputDialog.getText(
            self, "Подтверждение",
            "Введите мастер-пароль для экспорта:",
            QLineEdit.Password
        )

        if not ok or not password:
            QMessageBox.warning(self, "Ошибка", "Экспорт отменён")
            return

        if password != self.master_password:
            QMessageBox.warning(self, "Ошибка", "Неверный мастер-пароль")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Экспорт лога в {fmt.upper()}",
            f"audit_log.{fmt}", f"{fmt.upper()} files (*.{fmt})"
        )

        if file_path:
            db = Database(self.db_path)
            db.connect()
            formatter = LogFormatter(db)

            if fmt == 'json':
                formatter.export_json(file_path)
            elif fmt == 'csv':
                formatter.export_csv(file_path)

            db.close()
            QMessageBox.information(self, "Экспорт", f"Лог экспортирован в {file_path}")

            from src.core.events import event_system
            event_system.publish('export_performed', {'format': fmt, 'user': 'user'})

    def show_verification_details(self, entry, sequence_num):
        """Показ деталей с информацией о подписи и хеш-цепочке"""
        from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QDialogButtonBox, QTabWidget, QLabel
        from src.core.audit.log_verifier import LogVerifier
        from src.database.db import Database

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Детали записи #{sequence_num}")
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)

        tabs = QTabWidget()

        # Вкладка с JSON
        json_tab = QTextEdit()
        import json
        json_tab.setText(json.dumps(entry, indent=2, ensure_ascii=False))
        json_tab.setReadOnly(True)
        tabs.addTab(json_tab, "JSON")

        # Вкладка с верификацией
        verify_tab = QTextEdit()
        verify_tab.setReadOnly(True)

        if self.db_path:
            db = Database(self.db_path)
            db.connect()
            verifier = LogVerifier(db, self.master_password)

            # Проверяем конкретную запись
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT signature, previous_hash, entry_hash
                FROM audit_log WHERE sequence_number = ?
            """, (sequence_num,))
            row = cursor.fetchone()

            if row:
                signature_valid = verifier.signer.verify(
                    json.dumps(entry, sort_keys=True).encode('utf-8'),
                    bytes.fromhex(row[0])
                ) if verifier.signer else False

                verify_text = f"""
    === Результат верификации записи #{sequence_num} ===

    Подпись: {"ДЕЙСТВИТЕЛЬНА" if signature_valid else "НЕДЕЙСТВИТЕЛЬНА"}

    Хеш предыдущей записи: {row[1][:16]}...
    Хеш текущей записи: {row[2][:16]}...

    Хеш-цепочка: {"ЦЕЛА" if row[1] else "Начальная запись"}
    """
            else:
                verify_text = "Запись не найдена в БД"

            verify_tab.setText(verify_text)
            db.close()
        else:
            verify_tab.setText("Нет доступа к базе данных для проверки подписи")

        tabs.addTab(verify_tab, "Верификация")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()
