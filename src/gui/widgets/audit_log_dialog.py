from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QPushButton,
                               QHBoxLayout)
from PySide6.QtCore import Qt


class AuditLogDialog(QDialog):
    def __init__(self, parent=None, log_entries=None):
        super().__init__(parent)
        self.setWindowTitle("Журнал действий")
        self.resize(600, 400)
        self.setModal(True)

        self.log_entries = log_entries or []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Время", "Действие", "Запись", "Детали"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_data(self):
        self.table.setRowCount(0)

        for entry in self.log_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            timestamp = entry.get("timestamp", "")
            if hasattr(timestamp, 'strftime'):
                timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

            self.table.setItem(row, 0, QTableWidgetItem(str(timestamp)))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("action", "")))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("entry_title", "")))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get("details", "")))