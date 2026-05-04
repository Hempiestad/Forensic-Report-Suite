# peer_review.py
from PyQt5.QtWidgets import QAction, QInputDialog, QMessageBox, QFormLayout, QDialog, QLineEdit, QTextEdit
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor
from PyQt5.QtCore import Qt
from datetime import datetime
from security import compute_sha256  # For optional signature hash

class PeerReview:
    def __init__(self, editor, audit_logger, toolbar):
        self.editor = editor
        self.audit = audit_logger
        self.enabled = False
        self.reviewer_info = None
        self.change_formats = {
            'insert': QTextCharFormat(),
            'delete': QTextCharFormat()
        }
        self.setup_formats()

        # Toggle action
        self.toggle_action = QAction("Peer Review Mode: OFF", self.editor)
        self.toggle_action.setCheckable(True)
        self.toggle_action.triggered.connect(self.toggle_review_mode)
        toolbar.addSeparator()
        toolbar.addAction(self.toggle_action)

        # Comment action
        self.comment_action = QAction("Add Comment", self.editor)
        self.comment_action.triggered.connect(self.add_comment)
        self.comment_action.setEnabled(False)  # Enabled only in review mode
        toolbar.addAction(self.comment_action)

        # Sign-off action
        self.signoff_action = QAction("Sign Off Review", self.editor)
        self.signoff_action.triggered.connect(self.sign_off_review)
        self.signoff_action.setEnabled(False)
        toolbar.addAction(self.signoff_action)

        # Track text changes
        self.editor.textChanged.connect(self.track_changes)

    def setup_formats(self):
        insert_fmt = self.change_formats['insert']
        insert_fmt.setFontUnderline(True)
        insert_fmt.setUnderlineColor(QColor("green"))

        delete_fmt = self.change_formats['delete']
        delete_fmt.setFontStrikeOut(True)
        delete_fmt.setForeground(QColor("red"))

    def toggle_review_mode(self, checked):
        if checked:
            reviewer_name, ok = QInputDialog.getText(self.editor, "Reviewer Info", "Enter your name:")
            if not ok or not reviewer_name:
                self.toggle_action.setChecked(False)
                return
            agency, _ = QInputDialog.getText(self.editor, "Reviewer Info", "Enter your agency:")
            role, _ = QInputDialog.getText(self.editor, "Reviewer Info", "Enter your role:")

            self.reviewer_info = {
                "name": reviewer_name,
                "agency": agency,
                "role": role,
                "start_time": datetime.now().isoformat()
            }
            self.audit.log("PEER_REVIEW_STARTED", self.reviewer_info)
            self.enabled = True
            self.toggle_action.setText("Peer Review Mode: ON")
            self.comment_action.setEnabled(True)
            self.signoff_action.setEnabled(True)
            QMessageBox.information(self.editor, "Review Mode", "Review mode enabled. Changes will be tracked.")
        else:
            self.enabled = False
            self.toggle_action.setText("Peer Review Mode: OFF")
            self.comment_action.setEnabled(False)
            self.signoff_action.setEnabled(False)
            self.audit.log("PEER_REVIEW_ENDED", {"end_time": datetime.now().isoformat()})

    def track_changes(self):
        if not self.enabled:
            return
        # Basic tracking: apply formats on new text (advanced diffing can be added later)
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            # Assume deletion if selection
            fmt = self.change_formats['delete']
            cursor.mergeCharFormat(fmt)
        else:
            # Insertion
            fmt = self.change_formats['insert']
            cursor.mergeCharFormat(fmt)

    def add_comment(self):
        cursor = self.editor.textCursor()
        comment_text, ok = QInputDialog.getText(self.editor, "Add Comment", "Enter comment:")
        if ok and comment_text:
            comment_fmt = QTextCharFormat()
            comment_fmt.setBackground(QColor("yellow"))
            comment_fmt.setToolTip(f"Comment by {self.reviewer_info['name']} ({self.reviewer_info['role']}):\n{comment_text}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}")
            cursor.mergeCharFormat(comment_fmt)
            self.audit.log("COMMENT_ADDED", {"text": comment_text, "position": cursor.position()})

    def sign_off_review(self):
        dlg = QDialog(self.editor)
        dlg.setWindowTitle("Sign Off Review")
        layout = QFormLayout(dlg)

        summary_edit = QTextEdit()
        summary_edit.setPlaceholderText("Enter review summary or notes...")
        layout.addRow("Review Summary:", summary_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            summary = summary_edit.toPlainText()
            review_data = {**self.reviewer_info, "summary": summary, "end_time": datetime.now().isoformat()}
            # Optional hash for signature
            hash_input = f"{review_data['name']}{review_data['end_time']}{summary}"
            review_data["signature_hash"] = compute_sha256(hash_input.encode())

            self.audit.log("PEER_REVIEW_SIGNED_OFF", review_data)
            self.toggle_review_mode(False)  # End review mode
            QMessageBox.information(self.editor, "Signed Off", "Review signed off and logged.")