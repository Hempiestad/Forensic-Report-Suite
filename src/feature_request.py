# feature_request.py
# Feature Request Dialog for FuDog Labs Forensic Report Suite

import json
import platform
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from auth import load_config


class FeatureRequestDialog(QDialog):
    def __init__(self, parent=None, current_user=None, db_manager=None):
        super().__init__(parent)
        self.current_user = current_user or {"username": "anonymous", "role": "user"}
        self.db_manager = db_manager
        self.config = load_config()
        self.setWindowTitle("Request New Feature")
        self.setMinimumSize(620, 560)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel("Request a New Feature")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        user_group = QGroupBox("User Information")
        user_layout = QFormLayout(user_group)
        self.username_edit = QLineEdit(self.current_user.get("username", "anonymous"))
        self.username_edit.setReadOnly(True)
        user_layout.addRow("Username:", self.username_edit)
        self.role_edit = QLineEdit(self.current_user.get("role", "user"))
        self.role_edit.setReadOnly(True)
        user_layout.addRow("Role:", self.role_edit)
        layout.addWidget(user_group)

        system_group = QGroupBox("System Information")
        system_layout = QFormLayout(system_group)
        self.os_edit = QLineEdit(f"{platform.system()} {platform.release()}")
        self.os_edit.setReadOnly(True)
        system_layout.addRow("Operating System:", self.os_edit)
        self.python_edit = QLineEdit(f"Python {sys.version.split()[0]}")
        self.python_edit.setReadOnly(True)
        system_layout.addRow("Python Version:", self.python_edit)
        try:
            import PyQt5.QtCore

            qt_version = PyQt5.QtCore.QT_VERSION_STR
        except ImportError:
            qt_version = "Unknown"
        self.qt_edit = QLineEdit(f"PyQt5 {qt_version}")
        self.qt_edit.setReadOnly(True)
        system_layout.addRow("Qt Version:", self.qt_edit)
        layout.addWidget(system_group)

        details_group = QGroupBox("Feature Details")
        details_layout = QFormLayout(details_group)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        details_layout.addRow("Priority:", self.priority_combo)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Brief title for the feature request")
        details_layout.addRow("Title:", self.title_edit)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Describe the feature you want added...")
        details_layout.addRow("Description:", self.description_edit)
        self.benefits_edit = QTextEdit()
        self.benefits_edit.setPlaceholderText("Explain the benefit or problem it solves...")
        details_layout.addRow("Benefits:", self.benefits_edit)
        self.use_cases_edit = QTextEdit()
        self.use_cases_edit.setPlaceholderText("Add one or more examples of when this would be useful...")
        details_layout.addRow("Use Cases:", self.use_cases_edit)
        layout.addWidget(details_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.include_config_cb = QCheckBox("Include current configuration (anonymized)")
        self.include_config_cb.setChecked(False)
        options_layout.addWidget(self.include_config_cb)
        layout.addWidget(options_group)

        submit_group = QGroupBox("Submission")
        submit_layout = QFormLayout(submit_group)
        self.submit_combo = QComboBox()
        self.submit_combo.addItems(["Server API", "Save to File"])
        submit_layout.addRow("Method:", self.submit_combo)

        self.server_status_label = QLabel()
        submit_layout.addRow("Backend:", self.server_status_label)
        layout.addWidget(submit_group)

        button_layout = QHBoxLayout()
        self.submit_btn = QPushButton("Submit Request")
        self.submit_btn.clicked.connect(self.submit_request)
        button_layout.addWidget(self.submit_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.initialize_submission_mode()

    def initialize_submission_mode(self):
        server_enabled = bool(self.config.get("server_url"))
        if server_enabled:
            self.submit_combo.setCurrentText("Server API")
            self.server_status_label.setText("Configured server will forward this request by email.")
        else:
            self.submit_combo.setCurrentText("Save to File")
            self.server_status_label.setText("Server mode is not configured. Save to file is available.")
            self.submit_combo.model().item(0).setEnabled(False)

    def collect_request_data(self):
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "feature_request",
            "user": {
                "username": self.current_user.get("username", "anonymous"),
                "role": self.current_user.get("role", "user"),
            },
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "python": sys.version.split()[0],
                "pyqt5": self.qt_edit.text().replace("PyQt5 ", ""),
            },
            "feature": {
                "priority": self.priority_combo.currentText(),
                "title": self.title_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip(),
                "benefits": self.benefits_edit.toPlainText().strip(),
                "use_cases": self.use_cases_edit.toPlainText().strip(),
            },
        }

        if self.include_config_cb.isChecked():
            data["config"] = self.anonymize_config()

        return data

    def anonymize_config(self):
        config = self.config.copy()
        sensitive_keys = [
            "ad_server",
            "ad_domain",
            "ad_base_dn",
            "server_url",
            "feature_request_email",
            "bug_report_email",
        ]
        for key in sensitive_keys:
            if key in config:
                config[key] = "[REDACTED]"
        return config

    def submit_request(self):
        data = self.collect_request_data()
        if not data["feature"]["title"] or not data["feature"]["description"]:
            QMessageBox.warning(self, "Incomplete Request", "Please fill in at least the title and description.")
            return

        method = self.submit_combo.currentText()
        if method == "Server API":
            self.submit_via_api(data)
        else:
            self.save_to_file(data)

    def submit_via_api(self, data):
        if not self.db_manager or not getattr(self.db_manager, "token", None) or not self.config.get("server_url"):
            QMessageBox.warning(self, "Server Not Available", "Server mode is not configured or you are not authenticated.")
            return

        try:
            import requests

            server_url = self.config["server_url"].rstrip("/")
            headers = {"Authorization": f"Bearer {self.db_manager.token}"}
            response = requests.post(f"{server_url}/feature_requests", json=data, headers=headers, timeout=15)
            if response.ok:
                QMessageBox.information(self, "Request Submitted", "Feature request sent to the backend for email delivery.")
                self.accept()
                return

            error_message = response.text or f"Server returned error {response.status_code}."
            QMessageBox.warning(self, "Submission Failed", error_message)
        except Exception as e:
            QMessageBox.critical(self, "API Error", f"Failed to submit the feature request: {e}")

    def save_to_file(self, data):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Feature Request",
            "",
            "JSON Files (*.json);;Text Files (*.txt)",
        )
        if not file_path:
            return

        try:
            if file_path.endswith(".json"):
                with open(file_path, "w", encoding="utf-8") as file_handle:
                    json.dump(data, file_handle, indent=2)
            else:
                with open(file_path, "w", encoding="utf-8") as file_handle:
                    file_handle.write(f"Feature Request - {data['timestamp']}\n\n")
                    file_handle.write(f"User: {data['user']['username']} ({data['user']['role']})\n")
                    file_handle.write(f"System: {data['system']['os']}\n")
                    file_handle.write(f"Priority: {data['feature']['priority']}\n")
                    file_handle.write(f"Title: {data['feature']['title']}\n\n")
                    file_handle.write(f"Description:\n{data['feature']['description']}\n\n")
                    file_handle.write(f"Benefits:\n{data['feature']['benefits']}\n\n")
                    file_handle.write(f"Use Cases:\n{data['feature']['use_cases']}\n")
            QMessageBox.information(self, "Request Saved", f"Feature request saved to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save request: {e}")# feature_request.py
# Feature Request Dialog for FuDog Labs Forensic Report Suite

import sys
import os
import platform
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QMessageBox, QGroupBox, QFormLayout,
    QFileDialog, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal

class FeatureRequestDialog(QDialog):
    def __init__(self, parent=None, current_user=None, db_manager=None):
        super().__init__(parent)
        self.current_user = current_user or {"username": "anonymous", "role": "user"}
        self.db_manager = db_manager
        self.config = self.load_config()
        self.setWindowTitle("Request New Feature")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def load_config(self):
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                pass  # config load failure is non-critical
        return {}
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        # User Info Group
        user_group = QGroupBox("User Information")
        user_layout = QFormLayout(user_group)
        self.username_edit = QLineEdit(self.current_user.get('username', 'anonymous'))
        self.username_edit.setReadOnly(True)
        user_layout.addRow("Username:", self.username_edit)
        self.role_edit = QLineEdit(self.current_user.get('role', 'user'))
        self.role_edit.setReadOnly(True)
        user_layout.addRow("Role:", self.role_edit)
        layout.addWidget(user_group)

        # System Info Group
        system_group = QGroupBox("System Information")
        system_layout = QFormLayout(system_group)
        self.os_edit = QLineEdit(f"{platform.system()} {platform.release()}")
        self.os_edit.setReadOnly(True)
        system_layout.addRow("Operating System:", self.os_edit)
        self.python_edit = QLineEdit(f"Python {sys.version.split()[0]}")
        self.python_edit.setReadOnly(True)
        system_layout.addRow("Python Version:", self.python_edit)
        try:
            import PyQt5.QtCore
            qt_version = PyQt5.QtCore.QT_VERSION_STR
        except ImportError:
            qt_version = "Unknown"
        details_group = QGroupBox("Feature Details")
        details_layout = QFormLayout(details_group)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        details_layout.addRow("Priority:", self.priority_combo)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Brief title for the feature request")
        details_layout.addRow("Title:", self.title_edit)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Detailed description of the requested feature...")
        details_layout.addRow("Description:", self.description_edit)
        self.benefits_edit = QTextEdit()
        self.benefits_edit.setPlaceholderText("What benefits would this feature provide?...")
        details_layout.addRow("Benefits:", self.benefits_edit)
        self.use_cases_edit = QTextEdit()
        self.use_cases_edit.setPlaceholderText("Specific use cases or scenarios where this would be helpful...")
        details_layout.addRow("Use Cases:", self.use_cases_edit)
        layout.addWidget(details_group)

        # Options Group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.include_screenshots_cb = QCheckBox("Include screenshots (if available)")
        self.include_screenshots_cb.setChecked(False)
        options_layout.addWidget(self.include_screenshots_cb)
        self.include_config_cb = QCheckBox("Include current configuration (anonymized)")
        self.include_config_cb.setChecked(False)
        options_layout.addWidget(self.include_config_cb)
        layout.addWidget(options_group)

        # Submission Methods
        submit_group = QGroupBox("Submission Method")
        submit_layout = QVBoxLayout(submit_group)
        self.submit_combo = QComboBox()
        self.submit_combo.addItems(["Email", "Server API", "Save to File"])
        self.submit_combo.currentTextChanged.connect(self.on_submit_method_changed)
        submit_layout.addWidget(self.submit_combo)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("recipient@example.com")
        self.email_edit.setText(self.config.get('feature_request_email', 'features@forensic-app.com'))
        submit_layout.addWidget(self.email_edit)
        layout.addWidget(submit_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.submit_btn = QPushButton("Submit Request")
        self.submit_btn.clicked.connect(self.submit_request)
        button_layout.addWidget(self.submit_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.on_submit_method_changed("Email")  # Initialize

    def on_submit_method_changed(self, method):
        if method == "Email":
            self.email_edit.setEnabled(True)
            self.email_edit.setVisible(True)
        elif method == "Server API":
            self.email_edit.setEnabled(False)
            self.email_edit.setVisible(False)
        elif method == "Save to File":
            self.email_edit.setEnabled(False)
            self.email_edit.setVisible(False)

    def collect_request_data(self):
        """Collect all request data into a dictionary"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "feature_request",
            "user": {
                "username": self.current_user.get('username', 'anonymous'),
                "role": self.current_user.get('role', 'user')
            },
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "python": sys.version.split()[0],
                "pyqt5": getattr(sys.modules.get('PyQt5.QtCore', None), 'QT_VERSION_STR', 'Unknown') if 'PyQt5' in sys.modules else 'Unknown'
            },
            "feature": {
                "priority": self.priority_combo.currentText(),
                "title": self.title_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip(),
                "benefits": self.benefits_edit.toPlainText().strip(),
                "use_cases": self.use_cases_edit.toPlainText().strip()
            }
        }

        if self.include_config_cb.isChecked():
            data["config"] = self.anonymize_config()

        return data

    def anonymize_config(self):
        """Return anonymized config data"""
        config = self.config.copy()
        # Remove sensitive info
        sensitive_keys = ['ad_server', 'ad_domain', 'ad_base_dn', 'server_url', 'feature_request_email', 'bug_report_email']
        for key in sensitive_keys:
            if key in config:
                config[key] = "[REDACTED]"
        return config

    def submit_request(self):
        method = self.submit_combo.currentText()
        data = self.collect_request_data()

        # Validate required fields
        if not data["feature"]["title"] or not data["feature"]["description"]:
            QMessageBox.warning(self, "Incomplete Request", "Please fill in at least the title and description.")
            return

        if method == "Email":
            self.submit_via_email(data)
        elif method == "Server API":
            self.submit_via_api(data)
        elif method == "Save to File":
            self.save_to_file(data)

    def submit_via_email(self, data):
        email = self.email_edit.text().strip()
        if not email:
            QMessageBox.warning(self, "No Email", "Please enter a recipient email address.")
            return

        try:
            # Create email content
            msg = MIMEMultipart()
            msg['Subject'] = f"Feature Request: {data['feature']['title']}"
            msg['From'] = "forensic-app@localhost"  # Could be configurable
            msg['To'] = email

            body = f"""
Feature Request from FuDog Labs Forensic Report Suite

Timestamp: {data['timestamp']}
User: {data['user']['username']} ({data['user']['role']})
System: {data['system']['os']}, Python {data['system']['python']}, PyQt5 {data['system']['pyqt5']}

Priority: {data['feature']['priority']}
Title: {data['feature']['title']}

Description:
{data['feature']['description']}

Benefits:
{data['feature']['benefits']}

Use Cases:
{data['feature']['use_cases']}

"""

            if "config" in data:
                body += f"\n\nCurrent Configuration:\n{json.dumps(data['config'], indent=2)}"

            msg.attach(MIMEText(body, 'plain'))

            # Note: Actual email sending would require SMTP configuration
            # For now, just show the email content
            QMessageBox.information(self, "Email Preview",
                f"Email would be sent to: {email}\n\nSubject: {msg['Subject']}\n\nBody preview:\n{body[:500]}...")

            QMessageBox.information(self, "Request Submitted", "Feature request prepared for email submission.")

        except Exception as e:
            QMessageBox.critical(self, "Email Error", f"Failed to prepare email: {e}")

    def submit_via_api(self, data):
        if not self.db_manager or not hasattr(self.db_manager, 'token') or not self.config.get('server_url'):
            QMessageBox.warning(self, "Server Not Available", "Server mode not configured or not available.")
            return

        try:
            import requests
            server_url = self.config['server_url'].rstrip('/')
            headers = {'Authorization': f'Bearer {self.db_manager.token}'} if self.db_manager.token else {}
            resp = requests.post(f'{server_url}/feature_requests', json=data, headers=headers)
            if resp.ok:
                QMessageBox.information(self, "Request Submitted", "Feature request submitted to server successfully.")
            else:
                QMessageBox.warning(self, "Submission Failed", f"Server returned error: {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "API Error", f"Failed to submit via API: {e}")

    def save_to_file(self, data):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Feature Request", "", "JSON Files (*.json);;Text Files (*.txt)")
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                else:
                    with open(file_path, 'w') as f:
                        f.write(f"Feature Request - {data['timestamp']}\n\n")
                        f.write(f"User: {data['user']['username']} ({data['user']['role']})\n")
                        f.write(f"System: {data['system']['os']}\n")
                        f.write(f"Priority: {data['feature']['priority']}\n")
                        f.write(f"Title: {data['feature']['title']}\n\n")
                        f.write(f"Description:\n{data['feature']['description']}\n\n")
                        f.write(f"Benefits:\n{data['feature']['benefits']}\n\n")
                        f.write(f"Use Cases:\n{data['feature']['use_cases']}\n\n")
                QMessageBox.information(self, "Request Saved", f"Feature request saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save request: {e}")
