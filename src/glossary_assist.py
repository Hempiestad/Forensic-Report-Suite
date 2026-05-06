# glossary_assist.py
import os
import logging
from PyQt5.QtWidgets import (

    QToolTip, QWidget, QHBoxLayout, QLabel, QPushButton,
    QAction, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QObject, QEvent
from PyQt5.QtGui import QCursor, QFont, QTextCharFormat, QTextCursor, QPalette
from glossary import GLOSSARY

logger = logging.getLogger(__name__)

class GlossaryAssist(QObject):
    def __init__(self, editor, case_tab_instance):
        """
        editor: QTextEdit
        case_tab_instance: Reference to the CaseTab object (to add toolbar button and access export)
        """
        super().__init__(case_tab_instance)
        self.editor = editor
        self.case_tab = case_tab_instance
        self.enabled = True  # Configurable on/off

        self.suggestion_widget = None
        self.current_term = None
        self.used_terms = set()  # Track which terms already have footnotes
        self.footnote_counter = 1
        self.footnote_map = {}  # term -> footnote number

        # Load existing footnotes on init (in case report was loaded)
        self.scan_existing_footnotes()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check_current_word)

        self.editor.textChanged.connect(self.on_text_changed)

        # Add toggle button to toolbar
        self.toggle_action = QAction("Glossary Assist: ON", self.case_tab)
        self.toggle_action.setCheckable(True)
        self.toggle_action.setChecked(True)
        self.toggle_action.triggered.connect(self.toggle_assist)
        self.case_tab.toolbar.addSeparator()
        self.case_tab.toolbar.addAction(self.toggle_action)

    def show(self):
        """Entry point used by top-level Tools menu action."""
        if not self.enabled:
            QMessageBox.information(self.case_tab, "Glossary Assist", "Glossary Assist is currently disabled.")
            return

        self.check_current_word()
        if self.suggestion_widget:
            self.suggestion_widget.raise_()
            self.suggestion_widget.activateWindow()
            return

        QMessageBox.information(
            self.case_tab,
            "Glossary Assist",
            "Glossary Assist is active. Place the cursor on a SWGDE glossary term in the report editor to get a footnote suggestion."
        )

    def toggle_assist(self, checked):
        self.enabled = checked
        self.toggle_action.setText(f"Glossary Assist: {'ON' if checked else 'OFF'}")
        self.hide_suggestion()
        status = "enabled" if checked else "disabled"
        QMessageBox.information(self.case_tab, "Glossary Assist", f"Auto-glossary suggestions {status}.")

    def on_text_changed(self):
        if not self.enabled:
            return
        self.hide_suggestion()
        self.timer.start(800)  # Slight delay after typing stops

    def scan_existing_footnotes(self):
        """Scan document for existing footnotes to avoid duplicates and set counter"""
        html = self.editor.toHtml()
        import re
        # Find patterns like id="fn1" or name="fn1"
        ids = re.findall(r'id=["\']fn(\d+)["\']|name=["\']fn(\d+)["\']', html)
        numbers = {int(n) for tup in ids for n in tup if n}
        if numbers:
            self.footnote_counter = max(numbers) + 1

        # Extract used terms from existing footnotes
        for term in GLOSSARY:
            if f"id=\"fn" in html and term in html:
                # Simple heuristic — if term appears near a footnote, assume used
                # Better: parse footnote section
                pass  # We rely on user not manually duplicating

    def check_current_word(self):
        if not self.enabled:
            return

        try:
            cursor = self.editor.textCursor()
            probe = QTextCursor(cursor)
            probe.select(QTextCursor.WordUnderCursor)
            word = probe.selectedText().strip(".,!?;:()[]\"'")

            # If caret is after a trailing space/punctuation, probe previous word.
            if not word and probe.position() > 0:
                probe.movePosition(QTextCursor.Left)
                probe.select(QTextCursor.WordUnderCursor)
                word = probe.selectedText().strip(".,!?;:()[]\"'")

            if len(word) < 4 or word.lower() in self.used_terms:
                return

            for term in GLOSSARY:
                if word.lower() == term.lower():
                    if term in self.footnote_map:
                        return  # Already has footnote
                    self.current_term = term
                    self.show_suggestion(probe)
                    return
        except Exception as e:
            logger.warning(f"Error in check_current_word: {e}")
            return

    def show_suggestion(self, cursor):
        if self.suggestion_widget:
            return

        pos = self.editor.cursorRect(cursor).bottomRight()
        global_pos = self.editor.mapToGlobal(pos)

        self.suggestion_widget = QWidget()
        self.suggestion_widget.setObjectName("glossaryAssistPopup")
        self.suggestion_widget.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.suggestion_widget.setAttribute(Qt.WA_StyledBackground)
        self.suggestion_widget.setStyleSheet(self._build_popup_stylesheet())

        layout = QHBoxLayout(self.suggestion_widget)
        label = QLabel(f"<b>{self.current_term}</b> is a SWGDE glossary term")
        layout.addWidget(label)

        btn = QPushButton("Insert Footnote Link")
        btn.clicked.connect(self.insert_hyperlinked_footnote)
        layout.addWidget(btn)

        self.suggestion_widget.move(global_pos + QPoint(10, 10))
        self.suggestion_widget.show()

        self.editor.viewport().installEventFilter(self)

    def _build_popup_stylesheet(self):
        """Build popup styles from active Qt palette so the popup follows the selected theme."""
        pal = self.editor.palette()
        popup_bg = pal.color(QPalette.Window).name()
        popup_text = pal.color(QPalette.WindowText).name()
        border = pal.color(QPalette.Mid).name()
        button_bg = pal.color(QPalette.Button).name()
        button_text = pal.color(QPalette.ButtonText).name()
        hover_bg = pal.color(QPalette.Highlight).name()
        hover_text = pal.color(QPalette.HighlightedText).name()

        return f"""
            QWidget#glossaryAssistPopup {{
                background: {popup_bg};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 10px;
                color: {popup_text};
                font-size: 11pt;
            }}
            QWidget#glossaryAssistPopup QLabel {{
                color: {popup_text};
                background: transparent;
            }}
            QWidget#glossaryAssistPopup QPushButton {{
                background: {button_bg};
                color: {button_text};
                border: 1px solid {border};
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QWidget#glossaryAssistPopup QPushButton:hover {{
                background: {hover_bg};
                color: {hover_text};
            }}
        """

    def hide_suggestion(self):
        if self.suggestion_widget:
            self.editor.viewport().removeEventFilter(self)
            self.suggestion_widget.deleteLater()
            self.suggestion_widget = None
            self.current_term = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not self.suggestion_widget.geometry().contains(QCursor.pos()):
                self.hide_suggestion()
        return super().eventFilter(obj, event)

    def insert_hyperlinked_footnote(self):
        term = self.current_term
        definition = GLOSSARY[term]
        fn_num = self.footnote_counter
        fn_id = f"fn{fn_num}"
        ref_id = f"ref{fn_num}"

        pal = self.editor.palette()
        link_color = pal.color(QPalette.Link).name()
        backref_color = pal.color(QPalette.WindowText).name()

        cursor = self.editor.textCursor()

        # Insert clickable superscript link at cursor
        cursor.insertHtml(
            f'<a href="#{fn_id}" style="color: {link_color}; text-decoration: none;">'
            f'<sup>[{fn_num}]</sup></a>'
        )

        # Go to end to add footnote
        cursor.movePosition(cursor.End)
        cursor.insertBlock()
        cursor.insertHtml(
            f'<p id="{fn_id}">'
            f'<a href="#{ref_id}" style="text-decoration: none; color: {backref_color};">↩</a> '
            f'<b>[{fn_num}] {term}:</b> {definition}</p>'
        )

        # Optional: add back-reference anchor at original position
        # Not strictly needed — browser/PDF handles forward jump

        self.used_terms.add(term.lower())
        self.footnote_map[term] = fn_num
        self.footnote_counter += 1

        self.hide_suggestion()
        self.editor.ensureCursorVisible()
        
    # Notify audit logger if available
        if hasattr(self.case_tab, 'audit'):
            self.case_tab.audit.log_footnote_inserted(term, fn_num)

    # Optional: expose for export enhancements
    def get_footnote_anchors(self):
        """Return any needed anchor info for PDF"""
        return self.footnote_map