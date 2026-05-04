# legal_workflow_dialogs.py
# UI Dialogs for legal process approval workflow

import logging
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QDateEdit, QSpinBox, QComboBox, QFormLayout, QMessageBox,
    QGroupBox, QTabWidget
)
from PyQt5.QtCore import QDate, Qt, pyqtSignal

logger = logging.getLogger(__name__)


class InvestigatorApprovalDialog(QDialog):
    """Dialog for marking investigator approval of legal process"""
    
    approval_submitted = pyqtSignal(str, datetime, str)  # process_id, date, investigator_name
    
    def __init__(self, process_id: str, parent=None):
        super().__init__(parent)
        self.process_id = process_id
        self.approval_date = None
        self.investigator_name = ""
        
        self.setWindowTitle(f"Investigator Approval - {process_id}")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Info
        info_group = QGroupBox("Legal Process Information")
        info_layout = QFormLayout()
        
        process_label = QLabel(self.process_id)
        process_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addRow("Process ID:", process_label)
        
        stage_label = QLabel("1️⃣ Investigator Approval")
        stage_label.setStyleSheet("color: #20c997; font-weight: bold;")
        info_layout.addRow("Stage:", stage_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Approval details
        details_group = QGroupBox("Approval Details")
        details_layout = QFormLayout()
        
        # Investigator name
        self.investigator_input = QLineEdit()
        self.investigator_input.setPlaceholderText("e.g., Det. John Smith")
        details_layout.addRow("Investigator Name:", self.investigator_input)
        
        # Approval date
        self.approval_date_edit = QDateEdit()
        self.approval_date_edit.setCalendarPopup(True)
        self.approval_date_edit.setDate(QDate.currentDate())
        self.approval_date_edit.setFocusPolicy(Qt.StrongFocus)
        details_layout.addRow("Approval Date:", self.approval_date_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Notes
        notes_group = QGroupBox("Notes (Optional)")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Add any notes about the investigator's approval...\n"
            "Examples:\n"
            "- Any concerns or special conditions\n"
            "- Signature date and method"
        )
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Status indicator
        status_label = QLabel("✓ Ready to mark as approved")
        status_label.setStyleSheet("color: #28a745; font-style: italic;")
        layout.addWidget(status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.approve_btn = QPushButton("✓ Mark as Approved")
        self.approve_btn.clicked.connect(self.submit_approval)
        self.approve_btn.setDefault(True)
        self.approve_btn.setStyleSheet(
            "QPushButton { background-color: #20c997; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #1aa179; }"
        )
        button_layout.addWidget(self.approve_btn)
        
        layout.addLayout(button_layout)
    
    def submit_approval(self):
        """Validate and submit approval"""
        investigator_name = self.investigator_input.text().strip()
        
        if not investigator_name:
            QMessageBox.warning(self, "Missing Information", "Please enter investigator name.")
            return
        
        qdate = self.approval_date_edit.date()
        approval_date = datetime(qdate.year(), qdate.month(), qdate.day())
        
        reply = QMessageBox.question(
            self,
            "Confirm Investigator Approval",
            f"Mark investigator approval for {self.process_id}?\n\n"
            f"Investigator: {investigator_name}\n"
            f"Date: {approval_date.strftime('%B %d, %Y')}\n\n"
            "This will create a calendar event and notification.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.approval_submitted.emit(self.process_id, approval_date, investigator_name)
            self.accept()
    
    def get_data(self):
        """Get the approval data"""
        qdate = self.approval_date_edit.date()
        return {
            'process_id': self.process_id,
            'approval_date': datetime(qdate.year(), qdate.month(), qdate.day()),
            'investigator_name': self.investigator_input.text().strip(),
            'notes': self.notes_edit.toPlainText().strip()
        }


class StateAttorneyApprovalDialog(QDialog):
    """Dialog for marking state attorney approval"""
    
    approval_submitted = pyqtSignal(str, datetime, str)
    
    def __init__(self, process_id: str, parent=None):
        super().__init__(parent)
        self.process_id = process_id
        
        self.setWindowTitle(f"State Attorney Approval - {process_id}")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Info
        info_group = QGroupBox("Legal Process Information")
        info_layout = QFormLayout()
        
        process_label = QLabel(self.process_id)
        process_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addRow("Process ID:", process_label)
        
        stage_label = QLabel("2️⃣ State Attorney Approval")
        stage_label.setStyleSheet("color: #0dcaf0; font-weight: bold;")
        info_layout.addRow("Stage:", stage_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Approval details
        details_group = QGroupBox("Approval Details")
        details_layout = QFormLayout()
        
        # Attorney name
        self.attorney_input = QLineEdit()
        self.attorney_input.setPlaceholderText("e.g., ADA Sarah Doe")
        details_layout.addRow("Attorney Name:", self.attorney_input)
        
        # Approval date
        self.approval_date_edit = QDateEdit()
        self.approval_date_edit.setCalendarPopup(True)
        self.approval_date_edit.setDate(QDate.currentDate())
        details_layout.addRow("Approval Date:", self.approval_date_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Notes
        notes_group = QGroupBox("Notes (Optional)")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Add any notes about the state attorney's approval...\n"
            "Examples:\n"
            "- Any conditions or modifications requested\n"
            "- Office location or contact information"
        )
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.approve_btn = QPushButton("✓ Mark as Approved")
        self.approve_btn.clicked.connect(self.submit_approval)
        self.approve_btn.setDefault(True)
        self.approve_btn.setStyleSheet(
            "QPushButton { background-color: #0dcaf0; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #0bb5d5; }"
        )
        button_layout.addWidget(self.approve_btn)
        
        layout.addLayout(button_layout)
    
    def submit_approval(self):
        """Validate and submit approval"""
        attorney_name = self.attorney_input.text().strip()
        
        if not attorney_name:
            QMessageBox.warning(self, "Missing Information", "Please enter attorney name.")
            return
        
        qdate = self.approval_date_edit.date()
        approval_date = datetime(qdate.year(), qdate.month(), qdate.day())
        
        reply = QMessageBox.question(
            self,
            "Confirm State Attorney Approval",
            f"Mark state attorney approval for {self.process_id}?\n\n"
            f"Attorney: {attorney_name}\n"
            f"Date: {approval_date.strftime('%B %d, %Y')}\n\n"
            "This will create a calendar event and notification.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.approval_submitted.emit(self.process_id, approval_date, attorney_name)
            self.accept()
    
    def get_data(self):
        """Get the approval data"""
        qdate = self.approval_date_edit.date()
        return {
            'process_id': self.process_id,
            'approval_date': datetime(qdate.year(), qdate.month(), qdate.day()),
            'attorney_name': self.attorney_input.text().strip(),
            'notes': self.notes_edit.toPlainText().strip()
        }


class JudicialApprovalDialog(QDialog):
    """Dialog for marking judicial approval (judge signature)"""
    
    approval_submitted = pyqtSignal(str, datetime, str, str)  # process_id, date, court, judge
    
    def __init__(self, process_id: str, parent=None):
        super().__init__(parent)
        self.process_id = process_id
        
        self.setWindowTitle(f"Judicial Approval - {process_id}")
        self.setMinimumWidth(550)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Info
        info_group = QGroupBox("Legal Process Information")
        info_layout = QFormLayout()
        
        process_label = QLabel(self.process_id)
        process_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addRow("Process ID:", process_label)
        
        stage_label = QLabel("3️⃣ Judicial Approval (Judge Signature)")
        stage_label.setStyleSheet("color: #6f42c1; font-weight: bold;")
        info_layout.addRow("Stage:", stage_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Approval details
        details_group = QGroupBox("Judicial Approval Details")
        details_layout = QFormLayout()
        
        # Court name
        self.court_input = QLineEdit()
        self.court_input.setPlaceholderText("e.g., Circuit Court, District Court")
        details_layout.addRow("Court Name:", self.court_input)
        
        # Judge name
        self.judge_input = QLineEdit()
        self.judge_input.setPlaceholderText("e.g., Hon. Robert Brown")
        details_layout.addRow("Judge Name:", self.judge_input)
        
        # Approval date
        self.approval_date_edit = QDateEdit()
        self.approval_date_edit.setCalendarPopup(True)
        self.approval_date_edit.setDate(QDate.currentDate())
        details_layout.addRow("Signature Date:", self.approval_date_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Notes
        notes_group = QGroupBox("Notes (Optional)")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Add any notes about the judicial approval...\n"
            "Examples:\n"
            "- Order number or document reference\n"
            "- Any special conditions or limitations"
        )
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.approve_btn = QPushButton("✓ Mark as Approved")
        self.approve_btn.clicked.connect(self.submit_approval)
        self.approve_btn.setDefault(True)
        self.approve_btn.setStyleSheet(
            "QPushButton { background-color: #6f42c1; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #5a32a3; }"
        )
        button_layout.addWidget(self.approve_btn)
        
        layout.addLayout(button_layout)
    
    def submit_approval(self):
        """Validate and submit approval"""
        court_name = self.court_input.text().strip()
        judge_name = self.judge_input.text().strip()
        
        if not court_name or not judge_name:
            QMessageBox.warning(self, "Missing Information", "Please enter both court name and judge name.")
            return
        
        qdate = self.approval_date_edit.date()
        approval_date = datetime(qdate.year(), qdate.month(), qdate.day())
        
        reply = QMessageBox.question(
            self,
            "Confirm Judicial Approval",
            f"Mark judicial approval for {self.process_id}?\n\n"
            f"Court: {court_name}\n"
            f"Judge: {judge_name}\n"
            f"Date: {approval_date.strftime('%B %d, %Y')}\n\n"
            "This will create a calendar event and notification.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.approval_submitted.emit(self.process_id, approval_date, court_name, judge_name)
            self.accept()
    
    def get_data(self):
        """Get the approval data"""
        qdate = self.approval_date_edit.date()
        return {
            'process_id': self.process_id,
            'approval_date': datetime(qdate.year(), qdate.month(), qdate.day()),
            'court_name': self.court_input.text().strip(),
            'judge_name': self.judge_input.text().strip(),
            'notes': self.notes_edit.toPlainText().strip()
        }


class SendToProviderDialog(QDialog):
    """Dialog for marking document sent to provider (SLA clock starts here)"""
    
    sent_submitted = pyqtSignal(str, datetime, str, int)  # process_id, date, method, sla_days
    
    def __init__(self, process_id: str, provider_name: str = "", parent=None):
        super().__init__(parent)
        self.process_id = process_id
        self.provider_name = provider_name
        
        self.setWindowTitle(f"Send to Provider - {process_id}")
        self.setMinimumWidth(550)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Info
        info_group = QGroupBox("Legal Process Information")
        info_layout = QFormLayout()
        
        process_label = QLabel(self.process_id)
        process_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addRow("Process ID:", process_label)
        
        if self.provider_name:
            provider_label = QLabel(self.provider_name)
            info_layout.addRow("Provider:", provider_label)
        
        stage_label = QLabel("4️⃣ Send to Provider (⏱️ SLA CLOCK STARTS)")
        stage_label.setStyleSheet("color: #fd7e14; font-weight: bold;")
        info_layout.addRow("Stage:", stage_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Critical warning
        warning_label = QLabel(
            "⚠️ IMPORTANT: This is when the SLA (Service Level Agreement) clock starts!\n"
            "The SLA due date will be calculated from this transmission date.\n"
            "Provider response times are measured from this point."
        )
        warning_label.setStyleSheet(
            "background-color: #FFF3CD; padding: 10px; border: 2px solid #FFC107; "
            "border-radius: 4px; color: #856404; font-weight: bold;"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # Transmission details
        details_group = QGroupBox("Transmission Details")
        details_layout = QFormLayout()
        
        # Transmission method
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Law Enforcement Portal",
            "Certified Mail",
            "Email (with Read Receipt)",
            "in-person Delivery",
            "Other"
        ])
        details_layout.addRow("Transmission Method:", self.method_combo)
        
        # Transmission date
        self.sent_date_edit = QDateEdit()
        self.sent_date_edit.setCalendarPopup(True)
        self.sent_date_edit.setDate(QDate.currentDate())
        details_layout.addRow("Date Sent:", self.sent_date_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # SLA configuration
        sla_group = QGroupBox("SLA Configuration")
        sla_layout = QFormLayout()
        
        # Expected response days
        self.sla_days_spin = QSpinBox()
        self.sla_days_spin.setMinimum(1)
        self.sla_days_spin.setMaximum(180)
        self.sla_days_spin.setValue(45)
        self.sla_days_spin.setSuffix(" days")
        self.sla_days_spin.setToolTip("Number of days provider has to respond (from sent date)")
        self.sla_days_spin.valueChanged.connect(self.update_due_date_label)
        sla_layout.addRow("Expected Response Time:", self.sla_days_spin)
        
        # Calculate due date preview
        self.due_date_label = QLabel()
        self.update_due_date_label()
        self.due_date_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        sla_layout.addRow("Calculated Due Date:", self.due_date_label)
        
        sla_group.setLayout(sla_layout)
        layout.addWidget(sla_group)
        
        # Notes
        notes_group = QGroupBox("Notes (Optional)")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Add any notes about the transmission...\n"
            "Examples:\n"
            "- Tracking number\n"
            "- Recipient information\n"
            "- Any special instructions"
        )
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.send_btn = QPushButton("📤 Send to Provider")
        self.send_btn.clicked.connect(self.submit_send)
        self.send_btn.setDefault(True)
        self.send_btn.setStyleSheet(
            "QPushButton { background-color: #fd7e14; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #e67e22; }"
        )
        button_layout.addWidget(self.send_btn)
        
        layout.addLayout(button_layout)
    
    def update_due_date_label(self):
        """Update the SLA due date label"""
        qdate = self.sent_date_edit.date()
        sent_date = datetime(qdate.year(), qdate.month(), qdate.day())
        due_date = sent_date + timedelta(days=self.sla_days_spin.value())
        self.due_date_label.setText(due_date.strftime('%B %d, %Y'))
    
    def submit_send(self):
        """Validate and submit send"""
        qdate = self.sent_date_edit.date()
        sent_date = datetime(qdate.year(), qdate.month(), qdate.day())
        sla_days = self.sla_days_spin.value()
        
        due_date = sent_date + timedelta(days=sla_days)
        transmission_method = self.method_combo.currentText()
        
        reply = QMessageBox.question(
            self,
            "Confirm Send to Provider",
            f"Send {self.process_id} to provider?\n\n"
            f"Transmission Method: {transmission_method}\n"
            f"Date Sent: {sent_date.strftime('%B %d, %Y')}\n"
            f"SLA Response Time: {sla_days} days\n"
            f"Due Date: {due_date.strftime('%B %d, %Y')}\n\n"
            "⏱️ SLA clock will start from the sent date above.\n"
            "Calendar events will be created for send and due date.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.sent_submitted.emit(self.process_id, sent_date, transmission_method, sla_days)
            self.accept()
    
    def get_data(self):
        """Get the send data"""
        qdate = self.sent_date_edit.date()
        return {
            'process_id': self.process_id,
            'sent_date': datetime(qdate.year(), qdate.month(), qdate.day()),
            'transmission_method': self.method_combo.currentText(),
            'expected_response_days': self.sla_days_spin.value(),
            'notes': self.notes_edit.toPlainText().strip()
        }


class ProviderAcknowledgedDialog(QDialog):
    """Dialog for marking provider acknowledgment of receipt"""
    
    acknowledged_submitted = pyqtSignal(str, datetime)
    
    def __init__(self, process_id: str, provider_name: str = "", parent=None):
        super().__init__(parent)
        self.process_id = process_id
        self.provider_name = provider_name
        
        self.setWindowTitle(f"Provider Acknowledged - {process_id}")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Info
        info_group = QGroupBox("Legal Process Information")
        info_layout = QFormLayout()
        
        process_label = QLabel(self.process_id)
        process_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addRow("Process ID:", process_label)
        
        if self.provider_name:
            provider_label = QLabel(self.provider_name)
            info_layout.addRow("Provider:", provider_label)
        
        stage_label = QLabel("5️⃣ Provider Acknowledged")
        stage_label.setStyleSheet("color: #0d6efd; font-weight: bold;")
        info_layout.addRow("Stage:", stage_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Acknowledgment details
        details_group = QGroupBox("Acknowledgment Details")
        details_layout = QFormLayout()
        
        # Acknowledgment date
        self.ack_date_edit = QDateEdit()
        self.ack_date_edit.setCalendarPopup(True)
        self.ack_date_edit.setDate(QDate.currentDate())
        details_layout.addRow("Date Acknowledged:", self.ack_date_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Notes
        notes_group = QGroupBox("Notes (Optional)")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Add any notes about the provider acknowledgment...\n"
            "Examples:\n"
            "- Confirmation number\n"
            "- Contact person\n"
            "- Any relevant details"
        )
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.ack_btn = QPushButton("✓ Mark as Acknowledged")
        self.ack_btn.clicked.connect(self.submit_acknowledgment)
        self.ack_btn.setDefault(True)
        self.ack_btn.setStyleSheet(
            "QPushButton { background-color: #0d6efd; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #0a58ca; }"
        )
        button_layout.addWidget(self.ack_btn)
        
        layout.addLayout(button_layout)
    
    def submit_acknowledgment(self):
        """Validate and submit acknowledgment"""
        qdate = self.ack_date_edit.date()
        ack_date = datetime(qdate.year(), qdate.month(), qdate.day())
        
        reply = QMessageBox.question(
            self,
            "Confirm Provider Acknowledgment",
            f"Mark provider acknowledgment for {self.process_id}?\n\n"
            f"Date Acknowledged: {ack_date.strftime('%B %d, %Y')}\n\n"
            "This will create a calendar event and notification.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.acknowledged_submitted.emit(self.process_id, ack_date)
            self.accept()
    
    def get_data(self):
        """Get the acknowledgment data"""
        qdate = self.ack_date_edit.date()
        return {
            'process_id': self.process_id,
            'acknowledged_date': datetime(qdate.year(), qdate.month(), qdate.day()),
            'notes': self.notes_edit.toPlainText().strip()
        }


class MarkSLABreachDialog(QDialog):
    """Dialog for recording SLA breach when response is late"""
    
    breach_submitted = pyqtSignal(str, datetime, str)
    
    def __init__(self, process_id: str, sla_due_date: datetime, provider_name: str = "", parent=None):
        super().__init__(parent)
        self.process_id = process_id
        self.sla_due_date = sla_due_date
        self.provider_name = provider_name
        
        self.setWindowTitle(f"SLA Breach - {process_id}")
        self.setMinimumWidth(550)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Critical alert
        alert_label = QLabel(
            "🚨 SLA BREACH DETECTED\n\n"
            "The provider's response was received AFTER the SLA due date.\n"
            "This represents a failure to meet the Service Level Agreement."
        )
        alert_label.setStyleSheet(
            "background-color: #F8D7DA; padding: 12px; border: 2px solid #DC3545; "
            "border-radius: 4px; color: #721C24; font-weight: bold;"
        )
        alert_label.setWordWrap(True)
        layout.addWidget(alert_label)
        
        # Info
        info_group = QGroupBox("SLA Information")
        info_layout = QFormLayout()
        
        process_label = QLabel(self.process_id)
        process_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addRow("Process ID:", process_label)
        
        if self.provider_name:
            provider_label = QLabel(self.provider_name)
            info_layout.addRow("Provider:", provider_label)
        
        due_label = QLabel(self.sla_due_date.strftime('%B %d, %Y'))
        due_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        info_layout.addRow("Due Date:", due_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Breach details
        details_group = QGroupBox("Breach Details")
        details_layout = QFormLayout()
        
        # Response received date
        self.received_date_edit = QDateEdit()
        self.received_date_edit.setCalendarPopup(True)
        self.received_date_edit.setDate(QDate.currentDate())
        self.received_date_edit.valueChanged.connect(self.update_days_late)
        details_layout.addRow("Response Received Date:", self.received_date_edit)
        
        # Calculate days late
        self.days_late_label = QLabel()
        self.update_days_late()
        self.days_late_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        details_layout.addRow("Days Late:", self.days_late_label)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Breach reason
        reason_group = QGroupBox("Breach Reason (Optional)")
        reason_layout = QVBoxLayout()
        
        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(
            "Document why the provider failed to meet the SLA...\n"
            "Examples:\n"
            "- System issues on provider side\n"
            "- Large volume of data making retrieval difficult\n"
            "- Other extenuating circumstances"
        )
        self.reason_edit.setMaximumHeight(100)
        reason_layout.addWidget(self.reason_edit)
        
        reason_group.setLayout(reason_layout)
        layout.addWidget(reason_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.record_btn = QPushButton("🚨 Record SLA Breach")
        self.record_btn.clicked.connect(self.submit_breach)
        self.record_btn.setDefault(True)
        self.record_btn.setStyleSheet(
            "QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #c82333; }"
        )
        button_layout.addWidget(self.record_btn)
        
        layout.addLayout(button_layout)
    
    def update_days_late(self):
        """Update the days late calculation"""
        qdate = self.received_date_edit.date()
        received_date = datetime(qdate.year(), qdate.month(), qdate.day())
        days_late = (received_date - self.sla_due_date).days
        
        if days_late > 0:
            self.days_late_label.setText(f"{days_late} days (LATE)")
        elif days_late == 0:
            self.days_late_label.setText("On time (same day as due date)")
            self.days_late_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.days_late_label.setText(f"{abs(days_late)} days early (ON TIME)")
            self.days_late_label.setStyleSheet("color: #28a745; font-weight: bold;")
    
    def submit_breach(self):
        """Validate and submit breach"""
        qdate = self.received_date_edit.date()
        received_date = datetime(qdate.year(), qdate.month(), qdate.day())
        days_late = (received_date - self.sla_due_date).days
        
        if days_late <= 0:
            reply = QMessageBox.warning(
                self,
                "Not Actually a Breach",
                f"The response was received BEFORE or ON the due date.\n"
                f"Days early: {abs(days_late)}\n\n"
                "Do you want to record this as a breach anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        breach_reason = self.reason_edit.toPlainText().strip()
        
        reply = QMessageBox.question(
            self,
            "Confirm SLA Breach",
            f"Record SLA breach for {self.process_id}?\n\n"
            f"Due Date: {self.sla_due_date.strftime('%B %d, %Y')}\n"
            f"Response Date: {received_date.strftime('%B %d, %Y')}\n"
            f"Days Late: {days_late}\n"
            f"Reason: {breach_reason if breach_reason else '(None provided)'}\n\n"
            "A critical notification will be created and marked in red on calendar.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.breach_submitted.emit(self.process_id, received_date, breach_reason)
            self.accept()
    
    def get_data(self):
        """Get the breach data"""
        qdate = self.received_date_edit.date()
        received_date = datetime(qdate.year(), qdate.month(), qdate.day())
        return {
            'process_id': self.process_id,
            'received_date': received_date,
            'days_late': (received_date - self.sla_due_date).days,
            'breach_reason': self.reason_edit.toPlainText().strip()
        }
