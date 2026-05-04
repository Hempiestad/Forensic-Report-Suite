"""
Advanced Word Processing Module for FuDog Labs Forensic Report Suite
Provides Microsoft Office-style features for both Notes and Reports editors
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QComboBox, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QDialogButtonBox, QProgressBar, QStatusBar, QWidget
)
from PyQt5.QtGui import (
    QTextCharFormat, QTextBlockFormat, QFont, QColor, QTextCursor,
    QTextListFormat, QTextDocument
)
from PyQt5.QtCore import Qt, QTimer
import re

class FindReplaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find and Replace")
        self.setModal(False)
        self.editor = None
        self.last_match = None

        layout = QVBoxLayout(self)

        # Find section
        find_group = QGroupBox("Find")
        find_layout = QFormLayout(find_group)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Enter text to find...")
        find_layout.addRow("Find:", self.find_edit)
        layout.addWidget(find_group)

        # Replace section
        replace_group = QGroupBox("Replace")
        replace_layout = QFormLayout(replace_group)
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Enter replacement text...")
        replace_layout.addRow("Replace with:", self.replace_edit)
        layout.addWidget(replace_group)

        # Options
        options_layout = QHBoxLayout()
        self.case_sensitive_cb = QCheckBox("Case sensitive")
        self.whole_words_cb = QCheckBox("Whole words only")
        self.regex_cb = QCheckBox("Regular expression")
        options_layout.addWidget(self.case_sensitive_cb)
        options_layout.addWidget(self.whole_words_cb)
        options_layout.addWidget(self.regex_cb)
        layout.addLayout(options_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.find_btn = QPushButton("Find Next")
        self.find_btn.clicked.connect(self.find_next)
        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace)
        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)

        buttons_layout.addWidget(self.find_btn)
        buttons_layout.addWidget(self.replace_btn)
        buttons_layout.addWidget(self.replace_all_btn)
        buttons_layout.addWidget(self.close_btn)
        layout.addLayout(buttons_layout)

        self.find_edit.textChanged.connect(self.reset_search)

    def set_editor(self, editor):
        self.editor = editor

    def reset_search(self):
        self.last_match = None

    def get_search_flags(self):
        flags = 0
        if not self.case_sensitive_cb.isChecked():
            flags |= re.IGNORECASE
        return flags

    def find_next(self):
        if not self.editor:
            return

        text = self.find_edit.text()
        if not text:
            return

        cursor = self.editor.textCursor()
        document = self.editor.document()

        # Start from current position or beginning
        if self.last_match:
            cursor.setPosition(self.last_match + len(text))
        else:
            cursor.movePosition(QTextCursor.Start)

        if self.regex_cb.isChecked():
            try:
                pattern = re.compile(text, self.get_search_flags())
                full_text = document.toPlainText()
                match = pattern.search(full_text, cursor.position())
                if match:
                    start = match.start()
                    end = match.end()
                else:
                    # Wrap around
                    match = pattern.search(full_text, 0)
                    if match:
                        start = match.start()
                        end = match.end()
                    else:
                        QMessageBox.information(self, "Find", "Text not found.")
                        return
            except re.error as e:
                QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {e}")
                return
        else:
            # Plain text search
            flags = QTextDocument.FindFlags()
            if self.case_sensitive_cb.isChecked():
                flags |= QTextDocument.FindCaseSensitively
            if self.whole_words_cb.isChecked():
                flags |= QTextDocument.FindWholeWords

            found_cursor = document.find(text, cursor, flags)
            if found_cursor.isNull():
                # Wrap around
                cursor.movePosition(QTextCursor.Start)
                found_cursor = document.find(text, cursor, flags)
                if found_cursor.isNull():
                    QMessageBox.information(self, "Find", "Text not found.")
                    return

            start = found_cursor.selectionStart()
            end = found_cursor.selectionEnd()

        # Select the found text
        select_cursor = QTextCursor(document)
        select_cursor.setPosition(start)
        select_cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(select_cursor)
        self.last_match = start

    def replace(self):
        if not self.editor or not self.last_match:
            return

        replace_text = self.replace_edit.text()
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(replace_text)
            self.last_match = cursor.position()

    def replace_all(self):
        if not self.editor:
            return

        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()

        if not find_text:
            return

        document = self.editor.document()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()

        count = 0
        while True:
            if self.regex_cb.isChecked():
                try:
                    pattern = re.compile(find_text, self.get_search_flags())
                    full_text = document.toPlainText()
                    match = pattern.search(full_text, cursor.position())
                    if not match:
                        break
                    start = match.start()
                    end = match.end()
                except re.error:
                    break
            else:
                flags = QTextDocument.FindFlags()
                if self.case_sensitive_cb.isChecked():
                    flags |= QTextDocument.FindCaseSensitively
                if self.whole_words_cb.isChecked():
                    flags |= QTextDocument.FindWholeWords

                found_cursor = document.find(find_text, cursor, flags)
                if found_cursor.isNull():
                    break
                start = found_cursor.selectionStart()
                end = found_cursor.selectionEnd()

            # Replace
            replace_cursor = QTextCursor(document)
            replace_cursor.setPosition(start)
            replace_cursor.setPosition(end, QTextCursor.KeepAnchor)
            replace_cursor.insertText(replace_text)
            cursor.setPosition(start + len(replace_text))
            count += 1

        cursor.endEditBlock()
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences.")

class AdvancedTableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert Table")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Table properties
        table_group = QGroupBox("Table Properties")
        table_layout = QFormLayout(table_group)

        self.rows_spin = QSpinBox()
        self.rows_spin.setMinimum(1)
        self.rows_spin.setMaximum(50)
        self.rows_spin.setValue(3)
        table_layout.addRow("Rows:", self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setMinimum(1)
        self.cols_spin.setMaximum(50)
        self.cols_spin.setValue(3)
        table_layout.addRow("Columns:", self.cols_spin)

        self.border_spin = QSpinBox()
        self.border_spin.setMinimum(0)
        self.border_spin.setMaximum(10)
        self.border_spin.setValue(1)
        table_layout.addRow("Border width:", self.border_spin)

        layout.addWidget(table_group)

        # Cell properties
        cell_group = QGroupBox("Cell Properties")
        cell_layout = QFormLayout(cell_group)

        self.cell_padding_spin = QSpinBox()
        self.cell_padding_spin.setMinimum(0)
        self.cell_padding_spin.setMaximum(20)
        self.cell_padding_spin.setValue(5)
        cell_layout.addRow("Cell padding (px):", self.cell_padding_spin)

        self.cell_spacing_spin = QSpinBox()
        self.cell_spacing_spin.setMinimum(0)
        self.cell_spacing_spin.setMaximum(20)
        self.cell_spacing_spin.setValue(0)
        cell_layout.addRow("Cell spacing (px):", self.cell_spacing_spin)

        layout.addWidget(cell_group)

        # Style options
        style_group = QGroupBox("Style Options")
        style_layout = QVBoxLayout(style_group)

        self.header_row_cb = QCheckBox("First row is header")
        self.header_row_cb.setChecked(True)
        style_layout.addWidget(self.header_row_cb)

        self.alternate_rows_cb = QCheckBox("Alternate row colors")
        style_layout.addWidget(self.alternate_rows_cb)

        layout.addWidget(style_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_table_html(self):
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        border = self.border_spin.value()
        padding = self.cell_padding_spin.value()
        spacing = self.cell_spacing_spin.value()

        style = f'border-collapse: separate; border-spacing: {spacing}px;'
        if border > 0:
            style += f' border: {border}px solid #000000;'

        html = f'<table style="{style}">'

        for r in range(rows):
            if r == 0 and self.header_row_cb.isChecked():
                html += '<tr style="background-color: #f0f0f0; font-weight: bold;">'
            elif self.alternate_rows_cb.isChecked() and r % 2 == 1:
                html += '<tr style="background-color: #f9f9f9;">'
            else:
                html += '<tr>'

            for c in range(cols):
                cell_style = f'padding: {padding}px;'
                if border > 0:
                    cell_style += f' border: {border}px solid #cccccc;'

                if r == 0 and self.header_row_cb.isChecked():
                    html += f'<th style="{cell_style}">&nbsp;</th>'
                else:
                    html += f'<td style="{cell_style}">&nbsp;</td>'
            html += '</tr>'

        html += '</table>'
        return html

class WordProcessor:
    """Advanced word processing functionality for text editors"""

    def __init__(self, editor):
        self.editor = editor
        self.find_dialog = None
        self.format_history = []
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_indicator)

    def apply_strikethrough(self):
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontStrikeOut(not fmt.fontStrikeOut())
        cursor.setCharFormat(fmt)
        if not cursor.hasSelection():
            self.editor.setCurrentCharFormat(fmt)

    def apply_subscript(self):
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setVerticalAlignment(QTextCharFormat.AlignSubScript if fmt.verticalAlignment() != QTextCharFormat.AlignSubScript else QTextCharFormat.AlignNormal)
        cursor.setCharFormat(fmt)
        if not cursor.hasSelection():
            self.editor.setCurrentCharFormat(fmt)

    def apply_superscript(self):
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setVerticalAlignment(QTextCharFormat.AlignSuperScript if fmt.verticalAlignment() != QTextCharFormat.AlignSuperScript else QTextCharFormat.AlignNormal)
        cursor.setCharFormat(fmt)
        if not cursor.hasSelection():
            self.editor.setCurrentCharFormat(fmt)

    def insert_advanced_list(self, style):
        cursor = self.editor.textCursor()
        list_format = QTextListFormat()

        if style == "bullet":
            list_format.setStyle(QTextListFormat.ListDisc)
        elif style == "numbered":
            list_format.setStyle(QTextListFormat.ListDecimal)
        elif style == "alpha_upper":
            list_format.setStyle(QTextListFormat.ListUpperAlpha)
        elif style == "alpha_lower":
            list_format.setStyle(QTextListFormat.ListLowerAlpha)
        elif style == "roman_upper":
            list_format.setStyle(QTextListFormat.ListUpperRoman)
        elif style == "roman_lower":
            list_format.setStyle(QTextListFormat.ListLowerRoman)

        cursor.createList(list_format)

    def set_line_spacing(self, spacing_type):
        cursor = self.editor.textCursor()
        block_fmt = cursor.blockFormat()

        if spacing_type == "single":
            block_fmt.setLineHeight(100, QTextBlockFormat.SingleHeight)
        elif spacing_type == "1.5":
            block_fmt.setLineHeight(150, QTextBlockFormat.SingleHeight)
        elif spacing_type == "double":
            block_fmt.setLineHeight(200, QTextBlockFormat.SingleHeight)
        elif spacing_type == "exact":
            block_fmt.setLineHeight(120, QTextBlockFormat.FixedHeight)  # 12pt

        cursor.setBlockFormat(block_fmt)

    def set_paragraph_spacing(self, spacing_type):
        cursor = self.editor.textCursor()
        block_fmt = cursor.blockFormat()

        if spacing_type == "none":
            block_fmt.setTopMargin(0)
            block_fmt.setBottomMargin(0)
        elif spacing_type == "small":
            block_fmt.setTopMargin(5)
            block_fmt.setBottomMargin(5)
        elif spacing_type == "medium":
            block_fmt.setTopMargin(10)
            block_fmt.setBottomMargin(10)
        elif spacing_type == "large":
            block_fmt.setTopMargin(20)
            block_fmt.setBottomMargin(20)

        cursor.setBlockFormat(block_fmt)

    def apply_heading_style(self, level):
        cursor = self.editor.textCursor()
        block_fmt = cursor.blockFormat()

        if level == 1:
            block_fmt.setHeadingLevel(1)
            char_fmt = QTextCharFormat()
            char_fmt.setFontPointSize(24)
            char_fmt.setFontWeight(QFont.Bold)
            cursor.setBlockCharFormat(char_fmt)
        elif level == 2:
            block_fmt.setHeadingLevel(2)
            char_fmt = QTextCharFormat()
            char_fmt.setFontPointSize(18)
            char_fmt.setFontWeight(QFont.Bold)
            cursor.setBlockCharFormat(char_fmt)
        elif level == 3:
            block_fmt.setHeadingLevel(3)
            char_fmt = QTextCharFormat()
            char_fmt.setFontPointSize(14)
            char_fmt.setFontWeight(QFont.Bold)
            cursor.setBlockCharFormat(char_fmt)
        else:
            block_fmt.setHeadingLevel(0)
            char_fmt = QTextCharFormat()
            char_fmt.setFontPointSize(12)
            char_fmt.setFontWeight(QFont.Normal)
            cursor.setBlockCharFormat(char_fmt)

        cursor.setBlockFormat(block_fmt)

    def copy_format(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            block_fmt = cursor.blockFormat()
            self.format_history.append((fmt, block_fmt))
            if len(self.format_history) > 10:  # Keep only last 10 formats
                self.format_history.pop(0)

    def paste_format(self):
        if self.format_history:
            fmt, block_fmt = self.format_history[-1]
            cursor = self.editor.textCursor()

            if cursor.hasSelection():
                cursor.setCharFormat(fmt)
                cursor.setBlockFormat(block_fmt)
            else:
                self.editor.setCurrentCharFormat(fmt)
                cursor.setBlockFormat(block_fmt)

    def clear_formatting(self):
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        block_fmt = QTextBlockFormat()

        if cursor.hasSelection():
            cursor.setCharFormat(fmt)
            cursor.setBlockFormat(block_fmt)
        else:
            self.editor.setCurrentCharFormat(fmt)
            cursor.setBlockFormat(block_fmt)

    def show_find_replace(self):
        if not self.find_dialog:
            self.find_dialog = FindReplaceDialog(self.editor.parent())
        self.find_dialog.set_editor(self.editor)
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()

    def insert_advanced_table(self):
        dialog = AdvancedTableDialog(self.editor.parent())
        if dialog.exec_() == QDialog.Accepted:
            html = dialog.get_table_html()
            cursor = self.editor.textCursor()
            cursor.insertHtml(html)

    def auto_save_indicator(self):
        # This would be connected to a status bar
        pass

    def enable_auto_save(self, interval_ms=30000):  # 30 seconds
        self.auto_save_timer.start(interval_ms)

    def disable_auto_save(self):
        self.auto_save_timer.stop()
