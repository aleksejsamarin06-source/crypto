from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeManager:
    THEMES = ("system", "light", "dark")

    @classmethod
    def normalize(cls, theme: str) -> str:
        return theme if theme in cls.THEMES else "dark"

    @classmethod
    def resolve_theme(cls, theme: str) -> str:
        theme = cls.normalize(theme)
        if theme != "system":
            return theme
        return "light" if cls.windows_apps_use_light_theme() else "dark"

    @staticmethod
    def windows_apps_use_light_theme() -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return bool(value)
        except Exception:
            return False

    @classmethod
    def apply(cls, theme: str):
        app = QApplication.instance()
        if not app:
            return

        app.setStyle("Fusion")
        resolved = cls.resolve_theme(theme)
        if resolved == "light":
            app.setPalette(cls.light_palette())
            app.setStyleSheet(cls.light_stylesheet())
            return

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#303030"))
        palette.setColor(QPalette.WindowText, QColor("#f2f2f2"))
        palette.setColor(QPalette.Base, QColor("#252525"))
        palette.setColor(QPalette.AlternateBase, QColor("#333333"))
        palette.setColor(QPalette.ToolTipBase, QColor("#2f2f2f"))
        palette.setColor(QPalette.ToolTipText, QColor("#f2f2f2"))
        palette.setColor(QPalette.Text, QColor("#f2f2f2"))
        palette.setColor(QPalette.Button, QColor("#3d3d3d"))
        palette.setColor(QPalette.ButtonText, QColor("#f2f2f2"))
        palette.setColor(QPalette.BrightText, QColor("#ff6b6b"))
        palette.setColor(QPalette.Link, QColor("#7aa2ff"))
        palette.setColor(QPalette.Highlight, QColor("#446fba"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#9a9a9a"))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#9a9a9a"))
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#9a9a9a"))
        app.setPalette(palette)
        app.setStyleSheet(cls.dark_stylesheet())

    @staticmethod
    def dark_stylesheet() -> str:
        return """
            QMainWindow, QDialog {
                background-color: #303030;
                color: #f2f2f2;
            }
            QLabel, QCheckBox, QRadioButton {
                color: #f2f2f2;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget, QTreeWidget, QSpinBox {
                background-color: #252525;
                color: #f2f2f2;
                border: 1px solid #575757;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #446fba;
                selection-color: #ffffff;
            }
            QComboBox {
                background-color: #252525;
                color: #f2f2f2;
                border: 1px solid #575757;
                border-radius: 4px;
                padding: 4px 24px 4px 6px;
                selection-background-color: #446fba;
            }
            QComboBox::drop-down {
                border: 0;
                width: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                color: #f2f2f2;
                border: 1px solid #575757;
                selection-background-color: #446fba;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: #f2f2f2;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
            QPushButton:disabled {
                color: #9a9a9a;
                background-color: #343434;
                border-color: #4a4a4a;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #f2f2f2;
                border: 0;
                border-right: 1px solid #505050;
                border-bottom: 1px solid #505050;
                padding: 5px;
            }
            QTableWidget, QTreeWidget {
                gridline-color: #505050;
                alternate-background-color: #2e2e2e;
            }
            QTableWidget::item, QTreeWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected, QTreeWidget::item:selected {
                background-color: #446fba;
                color: #ffffff;
            }
            QMenu {
                background-color: #303030;
                color: #f2f2f2;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #446fba;
            }
            QMenuBar {
                background-color: #303030;
                color: #f2f2f2;
            }
            QMenuBar::item:selected {
                background-color: #3f3f3f;
            }
            QStatusBar {
                background-color: #2a2a2a;
                color: #f2f2f2;
            }
            QProgressBar {
                background-color: #252525;
                color: #f2f2f2;
                border: 1px solid #575757;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #446fba;
                border-radius: 3px;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #2b2b2b;
                border: 0;
                width: 12px;
                height: 12px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #5a5a5a;
                border-radius: 6px;
                min-height: 24px;
                min-width: 24px;
            }
            QScrollBar::handle:hover {
                background: #6a6a6a;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0;
                height: 0;
            }
        """

    @staticmethod
    def light_stylesheet() -> str:
        return """
            QMainWindow, QDialog {
                background-color: #f3f3f3;
                color: #202020;
            }
            QLabel, QCheckBox, QRadioButton {
                color: #202020;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget, QTreeWidget, QSpinBox {
                background-color: #ffffff;
                color: #202020;
                border: 1px solid #b8b8b8;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #2f6fca;
                selection-color: #ffffff;
            }
            QComboBox {
                background-color: #ffffff;
                color: #202020;
                border: 1px solid #b8b8b8;
                border-radius: 4px;
                padding: 4px 24px 4px 6px;
                selection-background-color: #2f6fca;
            }
            QComboBox::drop-down {
                border: 0;
                width: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #202020;
                border: 1px solid #b8b8b8;
                selection-background-color: #2f6fca;
                selection-color: #ffffff;
            }
            QPushButton {
                background-color: #e6e6e6;
                color: #202020;
                border: 1px solid #b8b8b8;
                border-radius: 5px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
            QPushButton:pressed {
                background-color: #d6d6d6;
            }
            QPushButton:disabled {
                color: #888888;
                background-color: #ededed;
                border-color: #d0d0d0;
            }
            QHeaderView::section {
                background-color: #e5e5e5;
                color: #202020;
                border: 0;
                border-right: 1px solid #c9c9c9;
                border-bottom: 1px solid #c9c9c9;
                padding: 5px;
            }
            QTableWidget, QTreeWidget {
                gridline-color: #d0d0d0;
                alternate-background-color: #f6f6f6;
            }
            QTableWidget::item, QTreeWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected, QTreeWidget::item:selected {
                background-color: #2f6fca;
                color: #ffffff;
            }
            QMenu {
                background-color: #ffffff;
                color: #202020;
                border: 1px solid #c8c8c8;
            }
            QMenu::item:selected {
                background-color: #2f6fca;
                color: #ffffff;
            }
            QMenuBar {
                background-color: #f3f3f3;
                color: #202020;
            }
            QMenuBar::item:selected {
                background-color: #e5e5e5;
            }
            QStatusBar {
                background-color: #eeeeee;
                color: #202020;
            }
            QProgressBar {
                background-color: #ffffff;
                color: #202020;
                border: 1px solid #b8b8b8;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2f6fca;
                border-radius: 3px;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #eeeeee;
                border: 0;
                width: 12px;
                height: 12px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #c0c0c0;
                border-radius: 6px;
                min-height: 24px;
                min-width: 24px;
            }
            QScrollBar::handle:hover {
                background: #a8a8a8;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0;
                height: 0;
            }
        """

    @staticmethod
    def light_palette() -> QPalette:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#f3f3f3"))
        palette.setColor(QPalette.WindowText, QColor("#202020"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#f6f6f6"))
        palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipText, QColor("#202020"))
        palette.setColor(QPalette.Text, QColor("#202020"))
        palette.setColor(QPalette.Button, QColor("#e6e6e6"))
        palette.setColor(QPalette.ButtonText, QColor("#202020"))
        palette.setColor(QPalette.BrightText, QColor("#d00000"))
        palette.setColor(QPalette.Link, QColor("#2f6fca"))
        palette.setColor(QPalette.Highlight, QColor("#2f6fca"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#888888"))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#888888"))
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#888888"))
        return palette
