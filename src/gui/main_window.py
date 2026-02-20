from src.core.events import event_system
from src.core.audit_manager import AuditManager
from src.gui.widgets.audit_log_dialog import AuditLogDialog
from PySide6.QtWidgets import QFileDialog
from src.database.db import Database
from src.database.backup import BackupManager
from src.gui.widgets.setup_wizard import SetupWizard
from src.database.db import Database
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                               QTableWidget, QTableWidgetItem, QStatusBar,
                               QMenuBar, QMenu, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from src.gui.widgets.entry_dialog import EntryDialog



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CryptoSafe Manager")
        self.resize(800, 600)

        self.entries_data = {}  # Словарь для хранения записей
        self.audit_manager = AuditManager()

        self.setup_menu()
        self.setup_table()
        self.setup_statusbar()

        self.check_first_run()

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Новый", self.run_setup_wizard)
        file_menu.addAction("Открыть", self.open_file)
        file_menu.addSeparator()
        file_menu.addAction("Резервная копия", self.backup)
        file_menu.addSeparator()
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

    def new_file(self):
        print("Новый файл")

    def open_file(self):
        print("Открыть файл")

    def backup(self):
        print("Резервная копия")

    def add_entry(self):
        dialog = EntryDialog(self, "Добавить запись")
        result = dialog.show()

        if result:
            new_id = len(self.entries_data) + 1
            self.entries_data[new_id] = result

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

            self.status_bar.showMessage(f"Статус: Не авторизован | Запись '{result['title']}' добавлена")

    def edit_entry(self):
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
            self.entries_data[entry_id] = result

            self.table.setItem(row, 1, QTableWidgetItem(result["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(result["username"]))
            self.table.setItem(row, 3, QTableWidgetItem(result["url"]))

            event_system.publish("entry_updated", {
                "id": entry_id,
                "title": result["title"],
                "details": f"Обновлена запись '{result['title']}'"
            })

            self.status_bar.showMessage(f"Статус: Не авторизован | Запись '{result['title']}' обновлена")

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

            event_system.publish("entry_deleted", {
                "id": entry_id,
                "title": title,
                "details": f"Удалена запись '{title}'"
            })

            if entry_id in self.entries_data:
                del self.entries_data[entry_id]

            self.table.removeRow(row)
            self.status_bar.showMessage(f"Статус: Не авторизован | Запись '{title}' удалена")

    def show_logs(self):
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

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть базу данных",
            os.path.expanduser("~"),
            "Database files (*.db)"
        )

        if file_path:
            db = Database(file_path)
            conn = db.connect()
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vault_entries'")
            if not cursor.fetchone():
                QMessageBox.warning(
                    self, "Ошибка",
                    "Этот файл не является базой данных CryptoSafe"
                )
                db.close()
                return

            cursor.execute("SELECT id, title, username, url FROM vault_entries")
            rows = cursor.fetchall()

            self.entries_data = {}
            self.table.setRowCount(0)

            for row in rows:
                entry_id = row[0]

                self.entries_data[entry_id] = {
                    "title": row[1],
                    "username": row[2] or "",
                    "url": row[3] or ""
                }

                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)
                self.table.setItem(row_pos, 0, QTableWidgetItem(str(entry_id)))
                self.table.setItem(row_pos, 1, QTableWidgetItem(row[1]))
                self.table.setItem(row_pos, 2, QTableWidgetItem(row[2] or ""))
                self.table.setItem(row_pos, 3, QTableWidgetItem(row[3] or ""))

            db.close()

            self.status_bar.showMessage(
                f"Статус: Открыта база {os.path.basename(file_path)} | Загружено {len(rows)} записей"
            )

    def backup(self):
        # DB-4 - заглушка для Sprint 8
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

    def check_first_run(self):
        # Проверка есть ли файл настроек или последняя открытая БД
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
            # Создание базы данных с мастер-паролем
            db_path = wizard.db_path
            master_password = wizard.master_password

            db = Database(db_path)
            db.connect()
            db.create_tables()
            db.close()

            self.current_db_path = db_path
            self.entries_data = {}
            self.table.setRowCount(0)

            self.status_bar.showMessage(f"Статус: База создана {os.path.basename(db_path)}")

            QMessageBox.information(
                self, "Готово",
                "Хранилище успешно создано"
            )