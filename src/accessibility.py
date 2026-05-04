# accessibility.py
import os
import logging
from PyQt5.QtWidgets import QAction, QMenu, QActionGroup
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import QSettings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Theme directory: themes/light.qss, themes/dark.qss, themes/high_contrast.qss
# Falls back to minimal inline QSS when files are not found (e.g. PyInstaller).
# ---------------------------------------------------------------------------

def _themes_dir() -> str:
    """Return absolute path to the themes/ directory next to this file."""
    try:
        import sys
        base = sys._MEIPASS  # PyInstaller bundle
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "themes")


def load_theme_qss(theme_name: str) -> str:
    """Load QSS for *theme_name* from the themes/ directory.

    Falls back to the corresponding inline constant if the file cannot be read.
    theme_name is one of: 'light', 'dark', 'high_contrast'.
    """
    file_map = {
        "light": "light.qss",
        "dark": "dark.qss",
        "high_contrast": "high_contrast.qss",
    }
    filename = file_map.get(theme_name, "dark.qss")
    qss_path = os.path.join(_themes_dir(), filename)
    try:
        with open(qss_path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        logger.warning("Could not load theme file %s, using inline fallback.", qss_path)
        fallbacks = {
            "light": _LIGHT_FALLBACK,
            "dark": _DARK_FALLBACK,
            "high_contrast": _HIGH_CONTRAST_FALLBACK,
        }
        return fallbacks.get(theme_name, _DARK_FALLBACK)


# ---------------------------------------------------------------------------
# Minimal inline fallback stylesheets (used only when .qss files are missing)
# NOTE: box-shadow and multi-font font-family are intentionally omitted as they
#       are not supported in QSS.
# ---------------------------------------------------------------------------

_LIGHT_FALLBACK = """
QMainWindow, QWidget {
    background-color: #f5f7fa;
    color: #1a1a2e;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #1a1a2e;
    border: 1px solid #c5ccd6;
    border-radius: 5px;
    padding: 6px 8px;
}
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #d0d7de;
    spacing: 4px;
    padding: 4px 6px;
}
QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
    min-width: 24px;
    min-height: 24px;
}
QToolButton:hover {
    background-color: #e3eaf6;
    border-color: #c5d3eb;
}
QPushButton {
    background-color: #ffffff;
    color: #1a1a2e;
    border: 1px solid #c5ccd6;
    border-radius: 6px;
    padding: 7px 16px;
    min-height: 28px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #e3eaf6;
    border-color: #1565c0;
    color: #1565c0;
}
QPushButton:pressed {
    background-color: #d0ddf5;
}
QLabel {
    color: #1a1a2e;
    background-color: transparent;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    color: #1a1a2e;
    border: 1px solid #c5ccd6;
    border-radius: 5px;
    padding: 5px 8px;
    min-height: 26px;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 4px;
}
QTabWidget::pane {
    border: 1px solid #d0d7de;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #eef1f5;
    color: #4a5568;
    padding: 8px 18px;
    border: 1px solid #d0d7de;
    border-bottom: none;
    border-radius: 6px 6px 0px 0px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1565c0;
    font-weight: bold;
    border-bottom: 2px solid #1565c0;
}
QMenuBar {
    background-color: #ffffff;
    color: #1a1a2e;
    border-bottom: 1px solid #d0d7de;
}
QMenuBar::item:selected {
    background-color: #e3eaf6;
    color: #1565c0;
}
QMenu {
    background-color: #ffffff;
    color: #1a1a2e;
    border: 1px solid #d0d7de;
    border-radius: 6px;
}
QMenu::item:selected {
    background-color: #e3eaf6;
    color: #1565c0;
}
QTreeWidget, QTreeView {
    background-color: #ffffff;
    color: #1a1a2e;
    border: 1px solid #d0d7de;
    border-radius: 6px;
}
QTableView, QTableWidget {
    background-color: #ffffff;
    color: #1a1a2e;
    gridline-color: #e0e4ea;
    alternate-background-color: #f7f9fb;
    border: 1px solid #d0d7de;
}
QHeaderView::section {
    background-color: #eef1f5;
    color: #1565c0;
    font-weight: bold;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #d0d7de;
    border-bottom: 2px solid #1565c0;
}
QScrollBar:vertical {
    background-color: #f5f7fa;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #b0bac8;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar:horizontal {
    background-color: #f5f7fa;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #b0bac8;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
}
"""

# Back-compat alias (code elsewhere may import these names)
LIGHT_STYLESHEET = _LIGHT_FALLBACK

_DARK_FALLBACK = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 5px;
    padding: 6px 8px;
}
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    spacing: 4px;
    padding: 4px 6px;
}
QPushButton {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #444c56;
    border-radius: 6px;
    padding: 7px 16px;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #2d333b;
    border-color: #58a6ff;
}
QLabel {
    color: #e6edf3;
    background-color: transparent;
}
QTabWidget::pane {
    background-color: #161b22;
    border: 1px solid #30363d;
}
QTabBar::tab {
    background-color: #0d1117;
    color: #8b949e;
    padding: 8px 18px;
    border: 1px solid #30363d;
    border-bottom: none;
    border-radius: 6px 6px 0px 0px;
}
QTabBar::tab:selected {
    background-color: #161b22;
    color: #58a6ff;
    font-weight: bold;
    border-bottom: 2px solid #58a6ff;
}
QMenuBar {
    background-color: #161b22;
    color: #e6edf3;
    border-bottom: 1px solid #30363d;
}
QMenu {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
}
QTreeWidget, QTreeView {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
}
QTableView, QTableWidget {
    background-color: #0d1117;
    color: #e6edf3;
    gridline-color: #21262d;
    alternate-background-color: #161b22;
}
QHeaderView::section {
    background-color: #161b22;
    color: #58a6ff;
    font-weight: bold;
    padding: 8px 10px;
    border-bottom: 2px solid #58a6ff;
}
QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar:horizontal {
    background-color: #0d1117;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
}
"""

# Back-compat alias
DARK_STYLESHEET = _DARK_FALLBACK

_HIGH_CONTRAST_FALLBACK = """
QMainWindow, QWidget {
    background-color: #000000;
    color: #ffffff;
    font-family: "Segoe UI";
    font-size: 11pt;
}
QTextEdit, QPlainTextEdit {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 6px 8px;
}
QToolBar {
    background-color: #000000;
    border-bottom: 2px solid #ffffff;
    spacing: 4px;
    padding: 4px 6px;
}
QPushButton {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 5px;
    padding: 9px 18px;
    min-height: 32px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #ffff00;
    color: #000000;
}
QPushButton:pressed {
    background-color: #ffffff;
    color: #000000;
}
QLabel {
    color: #ffffff;
    background-color: transparent;
    font-weight: bold;
}
QListWidget {
    background-color: #000000;
    border: 2px solid #ffffff;
    border-radius: 4px;
    color: #ffffff;
}
QTabWidget::pane {
    border: 2px solid #ffffff;
    background-color: #000000;
}
QTabBar::tab {
    background-color: #000000;
    color: #ffffff;
    padding: 10px 20px;
    border: 2px solid #ffffff;
    border-bottom: none;
    border-radius: 4px 4px 0px 0px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #000000;
}
QTabBar::tab:hover:!selected {
    background-color: #ffff00;
    color: #000000;
}
QMenuBar {
    background-color: #000000;
    color: #ffffff;
    border-bottom: 2px solid #ffffff;
}
QMenuBar::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QMenu {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
}
QMenu::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QTreeWidget, QTreeView {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
}
QTreeWidget::item:selected,
QTreeView::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QTableView, QTableWidget {
    background-color: #000000;
    color: #ffffff;
    gridline-color: #ffffff;
    alternate-background-color: #1a1a1a;
    border: 2px solid #ffffff;
}
QTableView::item:selected,
QTableWidget::item:selected {
    background-color: #ffff00;
    color: #000000;
    font-weight: bold;
}
QHeaderView::section {
    background-color: #ffffff;
    color: #000000;
    padding: 9px 10px;
    border: 1px solid #000000;
    font-weight: bold;
}
QScrollBar:vertical {
    background-color: #000000;
    width: 14px;
    border: 1px solid #555555;
}
QScrollBar::handle:vertical {
    background-color: #888888;
    min-height: 30px;
    border: 1px solid #ffffff;
}
QScrollBar::handle:vertical:hover {
    background-color: #ffff00;
}
QScrollBar:horizontal {
    background-color: #000000;
    height: 14px;
    border: 1px solid #555555;
}
QScrollBar::handle:horizontal {
    background-color: #888888;
    min-width: 30px;
    border: 1px solid #ffffff;
}
QScrollBar::handle:horizontal:hover {
    background-color: #ffff00;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
}
"""


# Back-compat alias
HIGH_CONTRAST_DARK = _HIGH_CONTRAST_FALLBACK

# Shared theme color tokens for consistent styling across widgets
THEME_COLOR_TOKENS = {
    'light': {
        'table': {
            'bg': '#f7f8fa',
            'alt_bg': '#eff1f4',
            'text': '#212529',
            'border': '#dee2e6',
            'header_bg': '#e4eaf4',
            'header_text': '#0056b3',
            'header_border': '#b3d9ff',
            'hover_bg': '#e8edf8',
            'hover_border': '#b3d9ff',
            'selected_bg': '#cce7ff',
            'selected_border': '#99d6ff',
            'child_bg': '#f0f2f6',
            'child_text': '#495057'
        },
        'child_row': {
            'label': '#0056b3',
            'secondary': '#495057',
            'bg': '#f0f2f6'
        },
        'dialog_table': {
            'bg': '#f7f8fa',
            'grid': '#dee2e6',
            'header_bg': '#e4eaf4',
            'header_text': '#0056b3',
            'border': '#dee2e6',
            'item_text': '#212529'
        }
    },
    'dark': {
        'table': {
            'bg': '#2d3748',
            'alt_bg': '#1a202c',
            'text': '#e2e8f0',
            'border': '#4a5568',
            'header_bg': '#4a5568',
            'header_text': '#e2e8f0',
            'header_border': '#718096',
            'hover_bg': '#4a5568',
            'hover_border': '#718096',
            'selected_bg': '#1a365d',
            'selected_border': '#63b3ed',
            'child_bg': '#1a202c',
            'child_text': '#cbd5e0'
        },
        'child_row': {
            'label': '#63b3ed',
            'secondary': '#cbd5e0',
            'bg': '#1a202c'
        },
        'dialog_table': {
            'bg': '#2d3748',
            'grid': '#4a5568',
            'header_bg': '#4a5568',
            'header_text': '#e2e8f0',
            'border': '#4a5568',
            'item_text': '#e2e8f0'
        }
    },
    'high_contrast': {
        'table': {
            'bg': '#000000',
            'alt_bg': '#1a1a1a',
            'text': '#ffffff',
            'border': '#ffffff',
            'header_bg': '#ffffff',
            'header_text': '#000000',
            'header_border': '#ffffff',
            'hover_bg': '#333333',
            'hover_border': '#ffffff',
            'selected_bg': '#333333',
            'selected_border': '#ffffff',
            'child_bg': '#1a1a1a',
            'child_text': '#ffffff'
        },
        'child_row': {
            'label': '#ffffff',
            'secondary': '#ffffff',
            'bg': '#1a1a1a'
        },
        'dialog_table': {
            'bg': '#000000',
            'grid': '#ffffff',
            'header_bg': '#ffffff',
            'header_text': '#000000',
            'border': '#ffffff',
            'item_text': '#ffffff'
        }
    }
}

class ThemeManager:
    def __init__(self, app, main_window):
        self.app = app
        self.main_window = main_window
        self.settings = QSettings("ForensicReportWriter", "Preferences")
        self.current_theme = self.settings.value("theme", "dark")
        self.theme_changed_callback = None

        # Theme-specific colors for table cells
        self.cell_colors = {
            'light': {
                'evidence_imaged': {'bg': '#28a745', 'text': '#ffffff', 'bold': False},
                'evidence_not_imaged': {'bg': '#ffc107', 'text': '#000000', 'bold': False},
                'evidence_other': {'bg': '#6c757d', 'text': '#ffffff', 'bold': False},
                'legal_completed': {'bg': '#28a745', 'text': '#ffffff', 'bold': False},
                'legal_pending': {'bg': '#ffc107', 'text': '#000000', 'bold': False},
                'legal_overdue': {'bg': '#dc3545', 'text': '#ffffff', 'bold': True},
                'legal_warning': {'bg': '#fd7e14', 'text': '#ffffff', 'bold': False},
                'leads_completed': {'bg': '#d3d3d3', 'text': '#000000', 'bold': False},
                'leads_pending': {'bg': '#ffffff', 'text': '#000000', 'bold': False},
            },
            'dark': {
                'evidence_imaged': {'bg': '#28a745', 'text': '#ffffff', 'bold': False},
                'evidence_not_imaged': {'bg': '#ffc107', 'text': '#000000', 'bold': False},
                'evidence_other': {'bg': '#6c757d', 'text': '#ffffff', 'bold': False},
                'legal_completed': {'bg': '#28a745', 'text': '#ffffff', 'bold': False},
                'legal_pending': {'bg': '#ffc107', 'text': '#000000', 'bold': False},
                'legal_overdue': {'bg': '#dc3545', 'text': '#ffffff', 'bold': True},
                'legal_warning': {'bg': '#fd7e14', 'text': '#ffffff', 'bold': False},
                'leads_completed': {'bg': '#4a5568', 'text': '#e2e8f0', 'bold': False},
                'leads_pending': {'bg': '#2d3748', 'text': '#e2e8f0', 'bold': False},
            },
            'high_contrast': {
                'evidence_imaged': {'bg': '#00ff00', 'text': '#000000', 'bold': True},
                'evidence_not_imaged': {'bg': '#ffff00', 'text': '#000000', 'bold': True},
                'evidence_other': {'bg': '#ffffff', 'text': '#000000', 'bold': True},
                'legal_completed': {'bg': '#00ff00', 'text': '#000000', 'bold': True},
                'legal_pending': {'bg': '#ffff00', 'text': '#000000', 'bold': True},
                'legal_overdue': {'bg': '#ff0000', 'text': '#ffffff', 'bold': True},
                'legal_warning': {'bg': '#ff8000', 'text': '#ffffff', 'bold': True},
                'leads_completed': {'bg': '#ffffff', 'text': '#000000', 'bold': True},
                'leads_pending': {'bg': '#000000', 'text': '#ffffff', 'bold': True},
            }
        }

        # Create theme submenu
        self.theme_menu = QMenu("Theme", self.main_window)
        self.theme_group = QActionGroup(self.main_window)
        self.theme_group.setExclusive(True)

        # Light theme action
        self.light_action = QAction("Light", self.main_window)
        self.light_action.setCheckable(True)
        self.light_action.triggered.connect(lambda: self.apply_theme("light"))
        self.theme_group.addAction(self.light_action)
        self.theme_menu.addAction(self.light_action)

        # Dark theme action
        self.dark_action = QAction("Dark", self.main_window)
        self.dark_action.setCheckable(True)
        self.dark_action.triggered.connect(lambda: self.apply_theme("dark"))
        self.theme_group.addAction(self.dark_action)
        self.theme_menu.addAction(self.dark_action)

        # High Contrast theme action
        self.high_contrast_action = QAction("High Contrast", self.main_window)
        self.high_contrast_action.setCheckable(True)
        self.high_contrast_action.triggered.connect(lambda: self.apply_theme("high_contrast"))
        self.theme_group.addAction(self.high_contrast_action)
        self.theme_menu.addAction(self.high_contrast_action)

        # The theme_menu is added to the View menu in main.py

        self.apply_theme(self.current_theme)

    def set_theme_changed_callback(self, callback):
        self.theme_changed_callback = callback

    def apply_theme(self, theme_name):
        qss = load_theme_qss(theme_name)
        self.app.setStyleSheet(qss)

        if theme_name == "dark":
            self.dark_action.setChecked(True)
        elif theme_name == "high_contrast":
            self.high_contrast_action.setChecked(True)
        else:  # light
            self.light_action.setChecked(True)

        self.current_theme = theme_name
        self.settings.setValue("theme", theme_name)

        # Call the callback if set
        if self.theme_changed_callback:
            self.theme_changed_callback()
