"""
Base Editor Class for Forensic Report Writing Application
Provides common functionality for Notes and Reports editors
"""

import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QToolBar, QAction,
    QStatusBar, QSplitter, QFrame, QMenu, QToolButton, QComboBox, QFontComboBox,
    QColorDialog, QProgressBar, QCheckBox, QSpinBox, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QInputDialog, QScrollArea, QSizePolicy
)
from PyQt5.QtGui import QTextCharFormat, QTextBlockFormat, QFont, QKeySequence, QColor, QTextCursor, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from word_processor import WordProcessor

class StatusBar(QStatusBar):
    """Enhanced status bar with comprehensive information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # Cursor position (hidden - not displayed to user)
        self.cursor_label = QLabel("Ln 1, Col 1")
        # self.addWidget(self.cursor_label)  # Commented out to hide cursor position

        # Word/character count
        self.word_count_label = QLabel("0 words, 0 characters")
        self.addWidget(self.word_count_label)

        # Zoom level
        self.zoom_label = QLabel("100%")
        self.addWidget(self.zoom_label)

        # Current formatting
        self.format_label = QLabel("Normal")
        self.addWidget(self.format_label)

        # Document status
        self.status_label = QLabel("Ready")
        self.addWidget(self.status_label)

    def update_cursor_position(self, line, column):
        self.cursor_label.setText(f"Ln {line}, Col {column}")

    def update_word_count(self, words, chars):
        self.word_count_label.setText(f"{words} words, {chars} characters")

    def update_zoom(self, zoom):
        self.zoom_label.setText(f"{zoom}%")

    def update_format(self, formats):
        format_text = []
        if formats.get('bold'): format_text.append('Bold')
        if formats.get('italic'): format_text.append('Italic')
        if formats.get('underline'): format_text.append('Underline')
        if not format_text:
            format_text = ['Normal']
        self.format_label.setText(', '.join(format_text))

    def update_status(self, status):
        self.status_label.setText(status)

class StyleManager:
    """Manages document styles and formatting presets"""

    def __init__(self):
        self.styles = self.load_default_styles()

    def load_default_styles(self):
        return {
            'Normal': {
                'font_family': 'Arial',
                'font_size': 12,
                'bold': False,
                'italic': False,
                'underline': False,
                'color': '#000000',
                'background': '#ffffff',
                'alignment': Qt.AlignLeft
            },
            'Heading 1': {
                'font_family': 'Arial',
                'font_size': 24,
                'bold': True,
                'italic': False,
                'underline': False,
                'color': '#000000',
                'background': '#ffffff',
                'alignment': Qt.AlignLeft
            },
            'Heading 2': {
                'font_family': 'Arial',
                'font_size': 18,
                'bold': True,
                'italic': False,
                'underline': False,
                'color': '#000000',
                'background': '#ffffff',
                'alignment': Qt.AlignLeft
            },
            'Heading 3': {
                'font_family': 'Arial',
                'font_size': 14,
                'bold': True,
                'italic': False,
                'underline': False,
                'color': '#000000',
                'background': '#ffffff',
                'alignment': Qt.AlignLeft
            },
            'Quote': {
                'font_family': 'Arial',
                'font_size': 12,
                'bold': False,
                'italic': True,
                'underline': False,
                'color': '#666666',
                'background': '#f0f0f0',
                'alignment': Qt.AlignLeft
            },
            'Code': {
                'font_family': 'Courier New',
                'font_size': 10,
                'bold': False,
                'italic': False,
                'underline': False,
                'color': '#000000',
                'background': '#f8f8f8',
                'alignment': Qt.AlignLeft
            }
        }

    def get_style(self, name):
        return self.styles.get(name, self.styles['Normal'])

    def apply_style(self, editor, style_name):
        style = self.get_style(style_name)
        cursor = editor.textCursor()

        # Apply character format
        char_format = QTextCharFormat()
        char_format.setFontFamily(style['font_family'])
        char_format.setFontPointSize(style['font_size'])
        char_format.setFontWeight(QFont.Bold if style['bold'] else QFont.Normal)
        char_format.setFontItalic(style['italic'])
        char_format.setFontUnderline(style['underline'])
        char_format.setForeground(QColor(style['color']))
        char_format.setBackground(QColor(style['background']))

        # Apply block format
        block_format = QTextBlockFormat()
        block_format.setAlignment(style['alignment'])

        if cursor.hasSelection():
            cursor.setCharFormat(char_format)
            cursor.setBlockFormat(block_format)
        else:
            editor.setCurrentCharFormat(char_format)
            cursor.setBlockFormat(block_format)

    def get_style_names(self):
        return list(self.styles.keys())

class BaseEditor(QWidget):
    """Base class for text editors with common functionality"""

    text_changed = pyqtSignal()
    cursor_position_changed = pyqtSignal(int, int)  # line, column

    def __init__(self, case_data, db_manager, audit_logger, parent=None):
        super().__init__(parent)
        self.case_data = case_data
        self.db = db_manager
        self.audit = audit_logger

        # Initialize components
        self.style_manager = StyleManager()
        self.word_processor = None
        self.zoom_level = 100

        # UI components
        self.editor = None
        self.status_bar = None
        self.toolbar = None

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Setup the basic UI structure"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Office-style toolbar
        self.toolbar = self.create_toolbar()
        layout.addWidget(self.toolbar)

        # Document canvas (gray desktop + white page)
        canvas = self.create_document_canvas()
        layout.addWidget(canvas, stretch=1)

        # Status bar
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)

        # Initialize word processor
        self.word_processor = WordProcessor(self.editor)

    def create_toolbar(self):
        """Create an Office-style grouped formatting toolbar."""
        toolbar = QToolBar("Formatting")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)

        # ── Group 1: Paragraph Style ──────────────────────────────────────
        self.style_combo = QComboBox()
        self.style_combo.setObjectName("toolbarCombo")
        self.style_combo.addItems(self.style_manager.get_style_names())
        self.style_combo.setFixedWidth(130)
        self.style_combo.setToolTip("Paragraph Style")
        self.style_combo.currentTextChanged.connect(self._on_style_combo_changed)
        toolbar.addWidget(self.style_combo)
        toolbar.addSeparator()

        # ── Group 2: Font Family + Size ───────────────────────────────────
        self.font_combo = QFontComboBox()
        self.font_combo.setObjectName("toolbarCombo")
        self.font_combo.setFixedWidth(170)
        self.font_combo.setToolTip("Font Family")
        self.font_combo.currentFontChanged.connect(self.change_font_family)
        toolbar.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setObjectName("toolbarCombo")
        self.size_combo.addItems([str(i) for i in [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]])
        self.size_combo.setCurrentText("12")
        self.size_combo.setFixedWidth(55)
        self.size_combo.setToolTip("Font Size")
        self.size_combo.setEditable(True)
        self.size_combo.currentTextChanged.connect(self.change_font_size)
        toolbar.addWidget(self.size_combo)
        toolbar.addSeparator()

        # ── Group 3: Character Formatting ────────────────────────────────
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setObjectName("formatBtnBold")
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.setShortcut(QKeySequence("Ctrl+B"))
        self.bold_btn.toggled.connect(self.toggle_bold)
        toolbar.addWidget(self.bold_btn)

        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setObjectName("formatBtnItalic")
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.setShortcut(QKeySequence("Ctrl+I"))
        self.italic_btn.toggled.connect(self.toggle_italic)
        toolbar.addWidget(self.italic_btn)

        self.underline_btn = QToolButton()
        self.underline_btn.setText("U")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setObjectName("formatBtnUnderline")
        self.underline_btn.setToolTip("Underline (Ctrl+U)")
        self.underline_btn.setShortcut(QKeySequence("Ctrl+U"))
        self.underline_btn.toggled.connect(self.toggle_underline)
        toolbar.addWidget(self.underline_btn)

        self.strike_btn = QToolButton()
        self.strike_btn.setText("S")
        self.strike_btn.setCheckable(True)
        self.strike_btn.setObjectName("formatBtnStrike")
        self.strike_btn.setToolTip("Strikethrough")
        self.strike_btn.toggled.connect(self.toggle_strikethrough)
        toolbar.addWidget(self.strike_btn)
        toolbar.addSeparator()

        # ── Group 4: Color ────────────────────────────────────────────────
        self.text_color_btn = QToolButton()
        self.text_color_btn.setText("A\u25be")
        self.text_color_btn.setObjectName("colorBtn")
        self.text_color_btn.setToolTip("Text Color")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        toolbar.addWidget(self.text_color_btn)

        self.highlight_btn = QToolButton()
        self.highlight_btn.setText("ab")
        self.highlight_btn.setObjectName("colorBtn")
        self.highlight_btn.setToolTip("Highlight Color")
        self.highlight_btn.clicked.connect(self.choose_highlight_color)
        toolbar.addWidget(self.highlight_btn)
        toolbar.addSeparator()

        # ── Group 5: Alignment ────────────────────────────────────────────
        self.align_left_btn = QToolButton()
        self.align_left_btn.setText("\u2261\u25c4")
        self.align_left_btn.setCheckable(True)
        self.align_left_btn.setChecked(True)
        self.align_left_btn.setToolTip("Align Left (Ctrl+L)")
        self.align_left_btn.setShortcut(QKeySequence("Ctrl+L"))
        self.align_left_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignLeft))
        toolbar.addWidget(self.align_left_btn)

        self.align_center_btn = QToolButton()
        self.align_center_btn.setText("\u2261")
        self.align_center_btn.setCheckable(True)
        self.align_center_btn.setToolTip("Center (Ctrl+E)")
        self.align_center_btn.setShortcut(QKeySequence("Ctrl+E"))
        self.align_center_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignHCenter))
        toolbar.addWidget(self.align_center_btn)

        self.align_right_btn = QToolButton()
        self.align_right_btn.setText("\u25ba\u2261")
        self.align_right_btn.setCheckable(True)
        self.align_right_btn.setToolTip("Align Right (Ctrl+R)")
        self.align_right_btn.setShortcut(QKeySequence("Ctrl+R"))
        self.align_right_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignRight))
        toolbar.addWidget(self.align_right_btn)

        self.align_justify_btn = QToolButton()
        self.align_justify_btn.setText("\u2263")
        self.align_justify_btn.setCheckable(True)
        self.align_justify_btn.setToolTip("Justify (Ctrl+J)")
        self.align_justify_btn.setShortcut(QKeySequence("Ctrl+J"))
        self.align_justify_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignJustify))
        toolbar.addWidget(self.align_justify_btn)
        self._align_buttons = [self.align_left_btn, self.align_center_btn,
                               self.align_right_btn, self.align_justify_btn]
        toolbar.addSeparator()

        # ── Group 6: Lists ────────────────────────────────────────────────
        list_btn = QToolButton()
        list_btn.setText("List \u25be")
        list_btn.setObjectName("listBtn")
        list_btn.setToolTip("Insert List")
        list_btn.setPopupMode(QToolButton.InstantPopup)
        list_menu = QMenu(self)
        for style_key, label in [
            ("bullet",      "\u2022 Bullet"),
            ("numbered",    "1. Numbered"),
            ("alpha_upper", "A. Uppercase Alpha"),
            ("alpha_lower", "a. Lowercase Alpha"),
            ("roman_upper", "I. Roman Numerals"),
            ("roman_lower", "i. Roman Numerals (lower)"),
        ]:
            act = QAction(label, self)
            act.triggered.connect(lambda checked, sk=style_key: self._insert_list(sk))
            list_menu.addAction(act)
        list_btn.setMenu(list_menu)
        toolbar.addWidget(list_btn)
        toolbar.addSeparator()

        # ── Group 7: Indent ───────────────────────────────────────────────
        outdent_btn = QToolButton()
        outdent_btn.setText("\u25c4 Outdent")
        outdent_btn.setObjectName("indentBtn")
        outdent_btn.setToolTip("Decrease Indent")
        outdent_btn.clicked.connect(self.decrease_indent)
        toolbar.addWidget(outdent_btn)

        indent_btn = QToolButton()
        indent_btn.setText("Indent \u25ba")
        indent_btn.setObjectName("indentBtn")
        indent_btn.setToolTip("Increase Indent")
        indent_btn.clicked.connect(self.increase_indent)
        toolbar.addWidget(indent_btn)
        toolbar.addSeparator()

        # ── Group 8: Zoom ─────────────────────────────────────────────────
        zoom_out_btn = QToolButton()
        zoom_out_btn.setText("\u2212")
        zoom_out_btn.setToolTip("Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)

        self.zoom_label_btn = QToolButton()
        self.zoom_label_btn.setText("100%")
        self.zoom_label_btn.setObjectName("zoomLabel")
        self.zoom_label_btn.setToolTip("Reset Zoom")
        self.zoom_label_btn.clicked.connect(self.reset_zoom)
        toolbar.addWidget(self.zoom_label_btn)

        zoom_in_btn = QToolButton()
        zoom_in_btn.setText("+")
        zoom_in_btn.setToolTip("Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)

        return toolbar

    def create_document_canvas(self):
        """Create a page-like document canvas: gray desktop with centered white page."""
        canvas = QScrollArea()
        canvas.setObjectName("documentCanvas")
        canvas.setWidgetResizable(True)

        wrapper = QWidget()
        wrapper.setObjectName("documentWrapper")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(24, 24, 24, 24)
        wrapper_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        self.editor = QTextEdit()
        self.editor.setObjectName("documentPage")
        self.editor.setAcceptRichText(True)
        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_context_menu)
        self.editor.document().setDocumentMargin(52)
        self.editor.setMinimumWidth(550)
        self.editor.setMaximumWidth(860)
        self.editor.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        wrapper_layout.addWidget(self.editor)
        canvas.setWidget(wrapper)
        return canvas

    def _on_style_combo_changed(self, style_name):
        """Handle style combo change, guarding against premature signals."""
        if self.editor is None or self.status_bar is None:
            return
        self.apply_style(style_name)

    def add_quick_format_buttons(self, toolbar):
        """Legacy method – kept for back-compat; no-op when create_toolbar is used."""
        pass

    def _insert_list(self, style_key: str) -> None:
        """Delegate to WordProcessor.insert_advanced_list if available."""
        if self.word_processor is not None:
            self.word_processor.insert_advanced_list(style_key)

    def setup_connections(self):
        """Setup signal connections"""
        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.editor.cursorPositionChanged.connect(self.update_toolbar_state)

        # Update timer for word count
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.start(1000)  # Update every second

    def on_text_changed(self):
        """Handle text changes"""
        self.text_changed.emit()
        self.update_statistics()

    def on_cursor_position_changed(self):
        """Handle cursor position changes"""
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock() + 1
        self.cursor_position_changed.emit(line, column)

    def update_statistics(self):
        """Update word count and other statistics"""
        text = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self.status_bar.update_word_count(words, chars)

    def apply_style(self, style_name):
        """Apply a named style"""
        self.style_manager.apply_style(self.editor, style_name)
        self.status_bar.update_status(f"Applied style: {style_name}")

    def toggle_bold(self, checked):
        """Toggle bold formatting"""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
            cursor.setCharFormat(fmt)
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self.editor.setCurrentCharFormat(fmt)

    def toggle_italic(self, checked):
        """Toggle italic formatting"""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontItalic(checked)
            cursor.setCharFormat(fmt)
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(checked)
        self.editor.setCurrentCharFormat(fmt)

    def toggle_underline(self, checked):
        """Toggle underline formatting"""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontUnderline(checked)
            cursor.setCharFormat(fmt)
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(checked)
        self.editor.setCurrentCharFormat(fmt)

    def toggle_strikethrough(self, checked):
        """Toggle strikethrough formatting"""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontStrikeOut(checked)
            cursor.setCharFormat(fmt)
        fmt = self.editor.currentCharFormat()
        fmt.setFontStrikeOut(checked)
        self.editor.setCurrentCharFormat(fmt)

    def choose_text_color(self):
        """Show color picker and apply text foreground color."""
        if self.editor is None:
            return
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            fmt = self.editor.currentCharFormat()
            fmt.setForeground(color)
            self.editor.setCurrentCharFormat(fmt)

    def choose_highlight_color(self):
        """Show color picker and apply text background (highlight) color."""
        if self.editor is None:
            return
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            fmt = self.editor.currentCharFormat()
            fmt.setBackground(color)
            self.editor.setCurrentCharFormat(fmt)

    def set_alignment(self, alignment):
        """Set paragraph alignment and update toolbar button states."""
        if self.editor is None:
            return
        self.editor.setAlignment(alignment)
        if not hasattr(self, '_align_buttons'):
            return
        align_map = {
            Qt.AlignLeft:    self.align_left_btn,
            Qt.AlignHCenter: self.align_center_btn,
            Qt.AlignRight:   self.align_right_btn,
            Qt.AlignJustify: self.align_justify_btn,
        }
        for align, btn in align_map.items():
            btn.blockSignals(True)
            btn.setChecked(bool(alignment & align))
            btn.blockSignals(False)

    def increase_indent(self):
        """Increase paragraph indent level."""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        block_fmt = cursor.blockFormat()
        block_fmt.setIndent(block_fmt.indent() + 1)
        cursor.setBlockFormat(block_fmt)

    def decrease_indent(self):
        """Decrease paragraph indent level."""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        block_fmt = cursor.blockFormat()
        block_fmt.setIndent(max(0, block_fmt.indent() - 1))
        cursor.setBlockFormat(block_fmt)

    def update_toolbar_state(self):
        """Sync toolbar button states to the current cursor character format."""
        if self.editor is None or not hasattr(self, 'bold_btn'):
            return
        fmt = self.editor.currentCharFormat()
        for btn, getter in [
            (self.bold_btn,      lambda f: f.fontWeight() == QFont.Bold),
            (self.italic_btn,    lambda f: f.fontItalic()),
            (self.underline_btn, lambda f: f.fontUnderline()),
            (self.strike_btn,    lambda f: f.fontStrikeOut()),
        ]:
            btn.blockSignals(True)
            btn.setChecked(getter(fmt))
            btn.blockSignals(False)
        if hasattr(self, 'font_combo'):
            self.font_combo.blockSignals(True)
            self.font_combo.setCurrentFont(fmt.font())
            self.font_combo.blockSignals(False)
        if hasattr(self, 'size_combo'):
            size = int(fmt.fontPointSize()) if fmt.fontPointSize() > 0 else 12
            self.size_combo.blockSignals(True)
            self.size_combo.setCurrentText(str(size))
            self.size_combo.blockSignals(False)
        if hasattr(self, '_align_buttons'):
            align = self.editor.alignment()
            align_map = {
                Qt.AlignLeft:    self.align_left_btn,
                Qt.AlignHCenter: self.align_center_btn,
                Qt.AlignRight:   self.align_right_btn,
                Qt.AlignJustify: self.align_justify_btn,
            }
            for a, btn in align_map.items():
                btn.blockSignals(True)
                btn.setChecked(bool(align & a))
                btn.blockSignals(False)

    def change_font_family(self, font):
        """Change font family"""
        if self.editor is None:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontFamily(font.family())
            cursor.setCharFormat(fmt)
        else:
            fmt = self.editor.currentCharFormat()
            fmt.setFontFamily(font.family())
            self.editor.setCurrentCharFormat(fmt)

    def change_font_size(self, size):
        """Change font size"""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontPointSize(int(size))
            cursor.setCharFormat(fmt)
        else:
            fmt = self.editor.currentCharFormat()
            fmt.setFontPointSize(int(size))
            self.editor.setCurrentCharFormat(fmt)

    def show_context_menu(self, position):
        """Show context menu at position"""
        menu = self.editor.createStandardContextMenu()

        # Add custom actions
        menu.addSeparator()
        menu.addAction("Apply Style", self.show_style_dialog)
        menu.addAction("Word Count", self.show_word_count_dialog)

        menu.exec_(self.editor.mapToGlobal(position))

    def show_style_dialog(self):
        """Show style selection dialog"""
        style_names = self.style_manager.get_style_names()
        style_name, ok = QInputDialog.getItem(self, "Apply Style", "Select style:", style_names, 0, False)
        if ok:
            self.apply_style(style_name)

    def show_word_count_dialog(self):
        """Show word count dialog"""
        text = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        chars_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

        msg = QMessageBox(self)
        msg.setWindowTitle("Word Count")
        msg.setText(f"Words: {words}\nCharacters: {chars}\nCharacters (no spaces): {chars_no_spaces}")
        msg.exec_()

    def zoom_in(self):
        """Zoom in"""
        if self.editor is None:
            return
        if self.zoom_level < 500:
            self.zoom_level += 25
            self.editor.zoomIn(1)
            self.status_bar.update_zoom(self.zoom_level)
            if hasattr(self, 'zoom_label_btn'):
                self.zoom_label_btn.setText(f"{self.zoom_level}%")

    def zoom_out(self):
        """Zoom out"""
        if self.editor is None:
            return
        if self.zoom_level > 25:
            self.zoom_level -= 25
            self.editor.zoomOut(1)
            self.status_bar.update_zoom(self.zoom_level)
            if hasattr(self, 'zoom_label_btn'):
                self.zoom_label_btn.setText(f"{self.zoom_level}%")

    def reset_zoom(self):
        """Reset zoom to 100%"""
        if self.editor is None:
            return
        while self.zoom_level > 100:
            self.zoom_out()
        while self.zoom_level < 100:
            self.zoom_in()

    def get_current_format(self):
        """Get current text formatting for status bar"""
        fmt = self.editor.currentCharFormat()
        return {
            'bold': fmt.fontWeight() == QFont.Bold,
            'italic': fmt.fontItalic(),
            'underline': fmt.fontUnderline()
        }
