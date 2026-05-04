#!/usr/bin/env python3
"""
Peer Review Portable Application
A standalone application for reviewing forensic reports offline.
Can be exported with report content and allows reviewers to add comments and track changes.
"""

import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit,
    QPushButton, QLabel, QInputDialog, QMessageBox, QSplitter, QDialog,
    QFormLayout, QDialogButtonBox, QTextBrowser, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
from PyQt5.QtCore import Qt, pyqtSlot

class PortablePeerReview(QMainWindow):
    def __init__(self, report_data=None):
        super().__init__()
        self.report_data = report_data or {}
        self.review_data = {
            "reviewer_info": {},
            "comments": [],
            "changes": [],
            "summary": "",
            "review_timestamp": None
        }
        self.setup_ui()
        self.load_report_data()

    def setup_ui(self):
        self.setWindowTitle("Portable Peer Review - Forensic Report")
        self.setMinimumSize(1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Header with case info
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Box)
        header_layout = QVBoxLayout(header_frame)

        self.case_info_label = QLabel("Case Information")
        self.case_info_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(self.case_info_label)

        layout.addWidget(header_frame)

        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Report viewer
        report_group = QGroupBox("Report Content")
        report_layout = QVBoxLayout(report_group)

        self.report_viewer = QTextEdit()
        self.report_viewer.setReadOnly(True)
        report_layout.addWidget(self.report_viewer)

        splitter.addWidget(report_group)

        # Review panel
        review_group = QGroupBox("Peer Review Panel")
        review_layout = QVBoxLayout(review_group)

        # Reviewer info section
        reviewer_group = QGroupBox("Reviewer Information")
        reviewer_layout = QFormLayout(reviewer_group)

        self.reviewer_name_label = QLabel("Not set")
        self.reviewer_agency_label = QLabel("Not set")
        self.reviewer_role_label = QLabel("Not set")

        reviewer_layout.addRow("Name:", self.reviewer_name_label)
        reviewer_layout.addRow("Agency:", self.reviewer_agency_label)
        reviewer_layout.addRow("Role:", self.reviewer_role_label)

        set_reviewer_btn = QPushButton("Set Reviewer Info")
        set_reviewer_btn.clicked.connect(self.set_reviewer_info)
        reviewer_layout.addRow(set_reviewer_btn)

        review_layout.addWidget(reviewer_group)

        # Comments section
        comments_group = QGroupBox("Comments")
        comments_layout = QVBoxLayout(comments_group)

        self.comments_list = QListWidget()
        comments_layout.addWidget(self.comments_list)

        add_comment_btn = QPushButton("Add Comment")
        add_comment_btn.clicked.connect(self.add_comment)
        comments_layout.addWidget(add_comment_btn)

        review_layout.addWidget(comments_group)

        # Changes tracking section
        changes_group = QGroupBox("Suggested Changes")
        changes_layout = QVBoxLayout(changes_group)

        self.changes_browser = QTextBrowser()
        self.changes_browser.setPlainText("No changes tracked yet.\n\nTo suggest changes, please use the main application with peer review mode enabled.")
        changes_layout.addWidget(self.changes_browser)

        review_layout.addWidget(changes_group)

        # Review summary
        summary_group = QGroupBox("Review Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_edit = QTextEdit()
        self.summary_edit.setPlaceholderText("Enter your review summary and recommendations...")
        summary_layout.addWidget(self.summary_edit)

        review_layout.addWidget(summary_group)

        splitter.addWidget(review_group)

        # Bottom buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save Review")
        save_btn.clicked.connect(self.save_review)
        button_layout.addWidget(save_btn)

        export_btn = QPushButton("Export Review File")
        export_btn.clicked.connect(self.export_review)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Set splitter proportions
        splitter.setSizes([700, 500])

    def load_report_data(self):
        if self.report_data:
            case_info = self.report_data.get('case_info', {})
            self.case_info_label.setText(f"Case: {case_info.get('case_number', 'Unknown')} - {case_info.get('title', 'No Title')}")

            # Load report HTML
            report_html = self.report_data.get('report_html', '')
            self.report_viewer.setHtml(report_html)

            # Load any existing review data
            if 'review_data' in self.report_data:
                self.load_existing_review(self.report_data['review_data'])

    def load_existing_review(self, review_data):
        self.review_data = review_data

        # Load reviewer info
        reviewer_info = review_data.get('reviewer_info', {})
        self.reviewer_name_label.setText(reviewer_info.get('name', 'Not set'))
        self.reviewer_agency_label.setText(reviewer_info.get('agency', 'Not set'))
        self.reviewer_role_label.setText(reviewer_info.get('role', 'Not set'))

        # Load comments
        self.comments_list.clear()
        for comment in review_data.get('comments', []):
            item_text = f"{comment['timestamp']} - {comment['text']}"
            self.comments_list.addItem(item_text)

        # Load summary
        self.summary_edit.setPlainText(review_data.get('summary', ''))

    def set_reviewer_info(self):
        name, ok = QInputDialog.getText(self, "Reviewer Name", "Enter your name:")
        if not ok or not name:
            return

        agency, ok = QInputDialog.getText(self, "Agency", "Enter your agency:")
        if not ok:
            return

        role, ok = QInputDialog.getText(self, "Role", "Enter your role:")
        if not ok:
            return

        self.review_data['reviewer_info'] = {
            "name": name,
            "agency": agency,
            "role": role
        }

        self.reviewer_name_label.setText(name)
        self.reviewer_agency_label.setText(agency)
        self.reviewer_role_label.setText(role)

    def add_comment(self):
        comment_text, ok = QInputDialog.getMultiLineText(self, "Add Comment", "Enter your comment:")
        if ok and comment_text.strip():
            comment = {
                "timestamp": datetime.now().isoformat(),
                "text": comment_text.strip()
            }
            self.review_data['comments'].append(comment)

            # Update UI
            item_text = f"{comment['timestamp']} - {comment['text']}"
            self.comments_list.addItem(item_text)

    def save_review(self):
        """Save review data to the report data structure"""
        self.review_data['summary'] = self.summary_edit.toPlainText()
        self.review_data['review_timestamp'] = datetime.now().isoformat()

        # Update the report data
        self.report_data['review_data'] = self.review_data

        QMessageBox.information(self, "Saved", "Review data saved successfully.")

    def export_review(self):
        """Export the reviewed report to a file"""
        from PyQt5.QtWidgets import QFileDialog

        self.save_review()  # Ensure latest data is saved

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Reviewed Report", "",
            "Reviewed Report Files (*.reviewed.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.report_data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(self, "Exported",
                    f"Reviewed report exported successfully:\n{file_path}")

            except Exception as e:
                QMessageBox.critical(self, "Export Error",
                    f"Failed to export review:\n{str(e)}")

def load_review_file(file_path):
    """Load a review file and return the data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        QMessageBox.critical(None, "Load Error", f"Failed to load review file:\n{str(e)}")
        return None

def main():
    app = QApplication(sys.argv)

    # Check if a file was passed as argument
    report_data = None
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            report_data = load_review_file(file_path)
        else:
            QMessageBox.warning(None, "File Not Found",
                f"Review file not found: {file_path}")

    window = PortablePeerReview(report_data)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
