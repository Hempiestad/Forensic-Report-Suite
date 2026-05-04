# bug_report.py
# Bug Reporting Dialog for FuDog Labs Forensic Report Suite

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

class BugReportDialog(QDialog):
    def __init__(self, parent=None, current_user=None, db_manager=None):
        super().__init__(parent)
        self.current_user = current_user or {"username": "anonymous", "role": "user"}
        self.db_manager = db_manager
        self.config = self.load_config()
        self.setWindowTitle("Report Bug or Error")
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
        details_group = QGroupBox("Bug Details")
        details_layout = QFormLayout(details_group)
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["Low", "Medium", "High", "Critical"])
        details_layout.addRow("Severity:", self.severity_combo)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Brief description of the issue")
        details_layout.addRow("Title:", self.title_edit)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Detailed description of the bug or error...")
        details_layout.addRow("Description:", self.description_edit)
        self.steps_edit = QTextEdit()
        self.steps_edit.setPlaceholderText("Steps to reproduce the issue...")
        details_layout.addRow("Steps to Reproduce:", self.steps_edit)
        layout.addWidget(details_group)

        # Options Group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.include_logs_cb = QCheckBox("Include recent application logs")
        self.include_logs_cb.setChecked(True)
        options_layout.addWidget(self.include_logs_cb)
        self.include_config_cb = QCheckBox("Include configuration (anonymized)")
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
        self.email_edit.setText(self.config.get('bug_report_email', ''))
        submit_layout.addWidget(self.email_edit)
        layout.addWidget(submit_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.submit_btn = QPushButton("Submit Report")
        self.submit_btn.clicked.connect(self.submit_report)
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

    def collect_report_data(self):
        """Collect all report data into a dictionary"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "user": {
                "username": self.current_user.get('username', 'anonymous'),
                "role": self.current_user.get('role', 'user')
            },
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "python": sys.version.split()[0],
                "pyqt5": getattr(sys.modules.get('PyQt5.QtCore', None), 'QT_VERSION_STR', 'Unknown') if 'PyQt5' in sys.modules else 'Unknown'
            },
            "bug": {
                "severity": self.severity_combo.currentText(),
                "title": self.title_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip(),
                "steps": self.steps_edit.toPlainText().strip()
            }
        }

        if self.include_logs_cb.isChecked():
            data["logs"] = self.collect_logs()

        if self.include_config_cb.isChecked():
            data["config"] = self.anonymize_config()

        return data

    def collect_logs(self):
        """Collect recent logs from audit files and general logs"""
        logs = {"audit_logs": [], "error_logs": []}

        # Collect from recent case audit logs
        cases_dir = "cases"
        if os.path.exists(cases_dir):
            for case_dir in os.listdir(cases_dir)[:5]:  # Limit to 5 recent cases
                audit_file = os.path.join(cases_dir, case_dir, "audit_trail.log")
                if os.path.exists(audit_file):
                    try:
                        with open(audit_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()[-10:]  # Last 10 entries
                            logs["audit_logs"].extend([f"{case_dir}: {line.strip()}" for line in lines])
                    except Exception as e:
                        logs["audit_logs"].append(f"Error reading {audit_file}: {e}")

        # Add any general error logs if they exist
        error_log_file = "error.log"
        if os.path.exists(error_log_file):
            try:
                with open(error_log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-20:]  # Last 20 lines
                    logs["error_logs"].extend(lines)
            except Exception as e:
                logs["error_logs"].append(f"Error reading error.log: {e}")

        return logs

    def anonymize_config(self):
        """Return anonymized config data"""
        config = self.config.copy()
        # Remove sensitive info
        sensitive_keys = ['ad_server', 'ad_domain', 'ad_base_dn', 'server_url', 'bug_report_email']
        for key in sensitive_keys:
            if key in config:
                config[key] = "[REDACTED]"
        return config

    def submit_report(self):
        method = self.submit_combo.currentText()
        data = self.collect_report_data()

        # Validate required fields
        if not data["bug"]["title"] or not data["bug"]["description"]:
            QMessageBox.warning(self, "Incomplete Report", "Please fill in at least the title and description.")
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
            msg['Subject'] = f"Bug Report: {data['bug']['title']}"
            msg['From'] = "forensic-app@localhost"  # Could be configurable
            msg['To'] = email

            body = f"""
Bug Report from FuDog Labs Forensic Report Suite

Timestamp: {data['timestamp']}
User: {data['user']['username']} ({data['user']['role']})
System: {data['system']['os']}, Python {data['system']['python']}, PyQt5 {data['system']['pyqt5']}

Severity: {data['bug']['severity']}
Title: {data['bug']['title']}

Description:
{data['bug']['description']}

Steps to Reproduce:
{data['bug']['steps']}

"""

            if "logs" in data:
                body += "\nRecent Logs:\n"
                for log_type, log_lines in data["logs"].items():
                    body += f"\n{log_type.upper()}:\n"
                    body += "\n".join(log_lines[-5:])  # Limit log lines

            if "config" in data:
                body += f"\n\nConfiguration:\n{json.dumps(data['config'], indent=2)}"

            msg.attach(MIMEText(body, 'plain'))

            # Note: Actual email sending would require SMTP configuration
            # For now, just show the email content
            QMessageBox.information(self, "Email Preview",
                f"Email would be sent to: {email}\n\nSubject: {msg['Subject']}\n\nBody preview:\n{body[:500]}...")

            QMessageBox.information(self, "Report Submitted", "Bug report prepared for email submission.")

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
            resp = requests.post(f'{server_url}/bug_reports', json=data, headers=headers)
            if resp.ok:
                QMessageBox.information(self, "Report Submitted", "Bug report submitted to server successfully.")
            else:
                QMessageBox.warning(self, "Submission Failed", f"Server returned error: {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "API Error", f"Failed to submit via API: {e}")

    def save_to_file(self, data):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Bug Report", "", "JSON Files (*.json);;Text Files (*.txt)")
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                else:
                    with open(file_path, 'w') as f:
                        f.write(f"Bug Report - {data['timestamp']}\n\n")
                        f.write(f"User: {data['user']['username']} ({data['user']['role']})\n")
                        f.write(f"System: {data['system']['os']}\n")
                        f.write(f"Severity: {data['bug']['severity']}\n")
                        f.write(f"Title: {data['bug']['title']}\n\n")
                        f.write(f"Description:\n{data['bug']['description']}\n\n")
                        f.write(f"Steps:\n{data['bug']['steps']}\n\n")
                        if "logs" in data:
                            f.write("Logs:\n")
                            for log_type, lines in data["logs"].items():
                                f.write(f"{log_type}:\n")
                                f.write("\n".join(lines))
                                f.write("\n\n")
                QMessageBox.information(self, "Report Saved", f"Bug report saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save report: {e}")

    def show_log_viewer(self):
        """Show a dialog with recent logs for user review"""
        logs = self.collect_logs()
        log_text = ""
        for log_type, lines in logs.items():
            log_text += f"{log_type.upper()}:\n"
            log_text += "\n".join(lines)
            log_text += "\n\n"

        if log_text.strip():
            from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QDialog, QDialogButtonBox
            dialog = QDialog(self)
            dialog.setWindowTitle("Recent Logs")
            dialog.setMinimumSize(600, 400)
            layout = QVBoxLayout(dialog)
            text_edit = QTextEdit()
            text_edit.setPlainText(log_text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(dialog.accept)
            layout.addWidget(buttons)
            dialog.exec_()
        else:
            QMessageBox.information(self, "No Logs", "No recent logs found.")
