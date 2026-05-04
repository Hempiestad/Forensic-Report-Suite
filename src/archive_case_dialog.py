# archive_case_dialog.py
# Dialog for archiving a case with reason and custom archive date

import logging
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QDateEdit, QCheckBox, QFormLayout, QMessageBox,
    QGroupBox
)
from PyQt5.QtCore import QDate, Qt

logger = logging.getLogger(__name__)


class ArchiveCaseDialog(QDialog):
    """Dialog for archiving a case"""
    
    def __init__(self, case_number: str, suspect_name: str, parent=None):
        super().__init__(parent)
        self.case_number = case_number
        self.suspect_name = suspect_name
        self.archive_date = None
        self.archive_reason = ""
        
        self.setWindowTitle(f"Archive Case - {case_number}")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Case info
        info_group = QGroupBox("Case Information")
        info_layout = QFormLayout()
        
        case_label = QLabel(self.case_number)
        case_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Case Number:", case_label)
        
        suspect_label = QLabel(self.suspect_name)
        info_layout.addRow("Suspect:", suspect_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Archive date options
        date_group = QGroupBox("Archive Date")
        date_layout = QVBoxLayout()
        
        # Default 30 days option
        self.default_date_radio = QCheckBox("Use default (30 days from today)")
        self.default_date_radio.setChecked(True)
        self.default_date_radio.toggled.connect(self.on_date_option_changed)
        date_layout.addWidget(self.default_date_radio)
        
        # Calculate 30 days from now
        default_date = datetime.now() + timedelta(days=30)
        default_date_label = QLabel(f"  → {default_date.strftime('%B %d, %Y')}")
        default_date_label.setStyleSheet("color: gray; font-style: italic; margin-left: 20px;")
        date_layout.addWidget(default_date_label)
        
        date_layout.addSpacing(10)
        
        # Custom date option
        custom_layout = QHBoxLayout()
        self.custom_date_radio = QCheckBox("Set custom archive date:")
        self.custom_date_radio.toggled.connect(self.on_date_option_changed)
        custom_layout.addWidget(self.custom_date_radio)
        
        self.custom_date_edit = QDateEdit()
        self.custom_date_edit.setCalendarPopup(True)
        self.custom_date_edit.setDate(QDate.currentDate().addDays(30))
        self.custom_date_edit.setMinimumDate(QDate.currentDate())
        self.custom_date_edit.setEnabled(False)
        custom_layout.addWidget(self.custom_date_edit)
        custom_layout.addStretch()
        
        date_layout.addLayout(custom_layout)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        # Archive reason
        reason_group = QGroupBox("Archive Reason (Optional)")
        reason_layout = QVBoxLayout()
        
        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(
            "Enter the reason for archiving this case...\n\n"
            "Examples:\n"
            "- Case completed and all documentation filed\n"
            "- Prosecution declined, no further action\n"
            "- Case transferred to another jurisdiction\n"
            "- Statute of limitations expired"
        )
        self.reason_edit.setMaximumHeight(120)
        reason_layout.addWidget(self.reason_edit)
        
        reason_group.setLayout(reason_layout)
        layout.addWidget(reason_group)
        
        # Warning message
        warning_label = QLabel(
            "⚠️ Archiving will remove this case from the active dashboard.\n"
            "You can view and restore archived cases from View > Archived Cases."
        )
        warning_label.setStyleSheet(
            "background-color: #FFF9E6; padding: 10px; border: 1px solid #FFD700; "
            "border-radius: 4px; color: #856404;"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.archive_btn = QPushButton("📦 Archive Case")
        self.archive_btn.clicked.connect(self.accept_archive)
        self.archive_btn.setDefault(True)
        self.archive_btn.setStyleSheet(
            "QPushButton { background-color: #FF8C00; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #FF7700; }"
        )
        button_layout.addWidget(self.archive_btn)
        
        layout.addLayout(button_layout)
    
    def on_date_option_changed(self):
        """Handle date option radio button changes"""
        use_custom = self.custom_date_radio.isChecked()
        self.custom_date_edit.setEnabled(use_custom)
        
        if use_custom:
            self.default_date_radio.setChecked(False)
        else:
            self.default_date_radio.setChecked(True)
    
    def accept_archive(self):
        """Validate and accept the archive request"""
        # Determine archive date
        if self.default_date_radio.isChecked():
            self.archive_date = datetime.now() + timedelta(days=30)
        else:
            qdate = self.custom_date_edit.date()
            self.archive_date = datetime(qdate.year(), qdate.month(), qdate.day())
        
        # Get reason (optional)
        self.archive_reason = self.reason_edit.toPlainText().strip()
        
        # Confirm
        date_str = self.archive_date.strftime('%B %d, %Y')
        
        reply = QMessageBox.question(
            self,
            "Confirm Archive",
            f"Archive case {self.case_number}?\n\n"
            f"Archive Date: {date_str}\n"
            f"Reason: {self.archive_reason if self.archive_reason else '(None provided)'}\n\n"
            "This case will be removed from the active dashboard.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.accept()
    
    def get_archive_data(self):
        """Get the archive date and reason"""
        return {
            'archive_date': self.archive_date,
            'archive_reason': self.archive_reason
        }
