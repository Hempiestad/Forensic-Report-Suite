# bug_report.py
# Bug Reporting Dialog for FuDog Labs Forensic Report Suite

import json
import os
import platform
import sys
from datetime import datetime

try:
    import keyring
except Exception:
    keyring = None

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
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
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from github_issue_helpers import (
    build_browser_issue_url,
    post_issue_via_api,
    redact_config_sections,
    resolve_repo_from_destination,
    test_issue_connection,
)


class BugReportDialog(QDialog):
    KEYRING_SERVICE = "ForensicReportSuite"
    KEYRING_USERNAME = "github_issue_api"

    def __init__(self, parent=None, current_user=None, db_manager=None):
        super().__init__(parent)
        self.current_user = current_user or {"username": "anonymous", "role": "user"}
        self.db_manager = db_manager
        self.config = self.load_config()

        self.setWindowTitle("Report Bug or Error")
        self.setMinimumSize(640, 480)
        self.resize(720, 600)
        self.setup_ui()

    def load_config(self):
        try:
            from auth import load_config

            return load_config()
        except Exception:
            config_path = "config.json"
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as file_handle:
                        return json.load(file_handle)
                except Exception:
                    pass
        return {}

    def setup_ui(self):
        # Outer layout: scrollable form on top, button bar pinned at bottom.
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 4, 4)

        title_label = QLabel("Report a Bug")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        intro_label = QLabel(
            "Capture enough detail for a useful issue without exposing more than you intend. "
            "The submission options below switch between browser, direct GitHub API, server, file, and email flows."
        )
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)

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
        self.description_edit.setMinimumHeight(120)
        details_layout.addRow("Description:", self.description_edit)

        self.steps_edit = QTextEdit()
        self.steps_edit.setPlaceholderText("Steps to reproduce the issue...")
        self.steps_edit.setMinimumHeight(100)
        details_layout.addRow("Steps to Reproduce:", self.steps_edit)

        layout.addWidget(details_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.include_logs_cb = QCheckBox("Include recent application logs")
        self.include_logs_cb.setChecked(True)
        options_layout.addWidget(self.include_logs_cb)

        self.include_config_cb = QCheckBox("Include configuration (anonymized)")
        self.include_config_cb.setChecked(False)
        options_layout.addWidget(self.include_config_cb)

        layout.addWidget(options_group)

        submit_group = QGroupBox("Submission")
        submit_layout = QFormLayout(submit_group)

        self.submit_combo = QComboBox()
        self.submit_combo.addItems([
            "GitHub Issues (Direct API)",
            "GitHub Issues (Browser)",
            "Server API",
            "Save to File",
            "Email (Preview)",
        ])
        self.submit_combo.currentTextChanged.connect(self.on_submit_method_changed)
        submit_layout.addRow("Method:", self.submit_combo)
        self.submit_layout = submit_layout

        self.submit_help_label = QLabel()
        self.submit_help_label.setWordWrap(True)
        submit_layout.addRow("Mode Details:", self.submit_help_label)

        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}

        self.github_destination_edit = QLineEdit()
        self.github_destination_edit.setPlaceholderText("owner/repo or full GitHub issue URL")
        self.github_destination_edit.setText(str(bug_cfg.get("github_repo", "")))
        submit_layout.addRow("GitHub Destination:", self.github_destination_edit)

        self.github_token_edit = QLineEdit()
        self.github_token_edit.setEchoMode(QLineEdit.Password)
        self.github_token_edit.setPlaceholderText("GitHub token (ghp_... or fine-grained token)")
        submit_layout.addRow("GitHub Token:", self.github_token_edit)

        self.test_github_btn = QPushButton("Test GitHub Connection")
        self.test_github_btn.clicked.connect(self.test_github_connection)
        submit_layout.addRow("", self.test_github_btn)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("recipient@example.com")
        self.email_edit.setText(str(bug_cfg.get("email") or self.config.get("bug_report_email", "")))
        submit_layout.addRow("Email Recipient:", self.email_edit)

        self.server_status_label = QLabel()
        self.server_status_label.setWordWrap(True)
        submit_layout.addRow("Backend:", self.server_status_label)

        layout.addWidget(submit_group)
        layout.addStretch()

        self._scroll.setWidget(container)
        outer_layout.addWidget(self._scroll)

        # Buttons are outside the scroll so they are always visible.
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 8, 0, 0)
        self.submit_btn = QPushButton("Submit Report")
        self.submit_btn.clicked.connect(self.submit_report)
        button_layout.addWidget(self.submit_btn)

        self.preview_logs_btn = QPushButton("Preview Logs")
        self.preview_logs_btn.clicked.connect(self.show_log_viewer)
        button_layout.addWidget(self.preview_logs_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        outer_layout.addLayout(button_layout)

        self.initialize_submission_mode()

    def initialize_submission_mode(self):
        server_enabled = bool(self.config.get("server_url")) if isinstance(self.config, dict) else False
        if server_enabled:
            self.server_status_label.setText("Server mode is configured.")
        else:
            self.server_status_label.setText("Server mode is not configured.")

        self.on_submit_method_changed(self.submit_combo.currentText())

    def on_submit_method_changed(self, method):
        is_github_api = method == "GitHub Issues (Direct API)"
        is_github_browser = method == "GitHub Issues (Browser)"
        is_github = is_github_api or is_github_browser
        is_server = method == "Server API"
        is_email = method == "Email (Preview)"

        mode_help = {
            "GitHub Issues (Direct API)": "Creates the issue immediately in the configured repository using your token.",
            "GitHub Issues (Browser)": "Opens a prefilled GitHub issue in your browser so you can review before submitting.",
            "Server API": "Sends the report to the configured application server if server mode is available.",
            "Save to File": "Exports the report content locally as JSON or plain text.",
            "Email (Preview)": "Builds the email subject and body preview without sending mail directly.",
        }
        self.submit_help_label.setText(mode_help.get(method, ""))

        self._set_form_row_visible(self.github_destination_edit, is_github)
        self._set_form_row_visible(self.github_token_edit, is_github_api)
        self.test_github_btn.setVisible(is_github_api)
        self._set_form_row_visible(self.email_edit, is_email)
        self._set_form_row_visible(self.server_status_label, is_server)

    def _set_form_row_visible(self, field, visible):
        label = self.submit_layout.labelForField(field)
        if label is not None:
            label.setVisible(visible)
        field.setVisible(visible)

    def collect_report_data(self):
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "bug_report",
            "user": {
                "username": self.current_user.get("username", "anonymous"),
                "role": self.current_user.get("role", "user"),
            },
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "python": sys.version.split()[0],
                "pyqt5": self.qt_edit.text().replace("PyQt5 ", ""),
            },
            "bug": {
                "severity": self.severity_combo.currentText(),
                "title": self.title_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip(),
                "steps": self.steps_edit.toPlainText().strip(),
            },
        }

        if self.include_logs_cb.isChecked():
            data["logs"] = self.collect_logs()

        if self.include_config_cb.isChecked():
            data["config"] = self.anonymize_config()

        return data

    def collect_logs(self):
        logs = {"audit_logs": [], "error_logs": []}

        cases_dir = "cases"
        if os.path.exists(cases_dir):
            for case_dir in os.listdir(cases_dir)[:5]:
                audit_file = os.path.join(cases_dir, case_dir, "audit_trail.log")
                if os.path.exists(audit_file):
                    try:
                        with open(audit_file, "r", encoding="utf-8") as file_handle:
                            lines = file_handle.readlines()[-10:]
                            logs["audit_logs"].extend([f"{case_dir}: {line.strip()}" for line in lines])
                    except Exception as exc:
                        logs["audit_logs"].append(f"Error reading {audit_file}: {exc}")

        error_log_file = "error.log"
        if os.path.exists(error_log_file):
            try:
                with open(error_log_file, "r", encoding="utf-8") as file_handle:
                    lines = file_handle.readlines()[-20:]
                    logs["error_logs"].extend([line.rstrip("\n") for line in lines])
            except Exception as exc:
                logs["error_logs"].append(f"Error reading error.log: {exc}")

        return logs

    def anonymize_config(self):
        config_copy = dict(self.config) if isinstance(self.config, dict) else {}
        sensitive_keys = [
            "ad_server",
            "ad_domain",
            "ad_base_dn",
            "server_url",
            "bug_report_email",
            "github_token",
        ]

        redact_config_sections(config_copy, ["bug_report"])

        for key in sensitive_keys:
            if key in config_copy:
                config_copy[key] = "[REDACTED]"

        return config_copy

    def submit_report(self):
        data = self.collect_report_data()

        if not data["bug"]["title"] or not data["bug"]["description"]:
            QMessageBox.warning(self, "Incomplete Report", "Please fill in at least the title and description.")
            return

        method = self.submit_combo.currentText()
        if method == "GitHub Issues (Direct API)":
            self.submit_to_github_api(data)
        elif method == "GitHub Issues (Browser)":
            self.submit_to_github_browser(data)
        elif method == "Server API":
            self.submit_via_api(data)
        elif method == "Save to File":
            self.save_to_file(data)
        else:
            self.submit_via_email_preview(data)

    def _resolve_github_destination(self):
        typed = self.github_destination_edit.text().strip()
        if typed:
            return typed

        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}
        # Fall back to the legacy better_bugs_url key if github_repo is not set.
        return str(
            bug_cfg.get("github_repo")
            or bug_cfg.get("better_bugs_url", "")
        ).strip()

    def _resolve_github_token(self):
        typed = self.github_token_edit.text().strip()
        if typed:
            return typed

        # Prefer secure OS-backed storage before environment/config fallbacks.
        keyring_token = self._get_github_token_from_keyring()
        if keyring_token:
            return keyring_token

        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}
        env_var_name = str(bug_cfg.get("github_token_env", "GITHUB_TOKEN")).strip() or "GITHUB_TOKEN"
        env_token = os.environ.get(env_var_name, "").strip()
        if env_token:
            return env_token

        return str(bug_cfg.get("github_token", "")).strip()

    def _get_github_token_from_keyring(self):
        if keyring is None:
            return ""

        try:
            token = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME)
        except Exception:
            return ""
        return str(token or "").strip()

    def _resolve_github_repo(self):
        return resolve_repo_from_destination(self._resolve_github_destination())

    def _build_issue_body(self, data):
        lines = [
            "## Bug Report",
            f"- Severity: {data['bug']['severity']}",
            f"- User: {data['user']['username']} ({data['user']['role']})",
            f"- Timestamp: {data['timestamp']}",
            f"- System: {data['system']['os']}",
            f"- Python: {data['system']['python']}",
            f"- PyQt5: {data['system']['pyqt5']}",
            "",
            "## Description",
            data["bug"]["description"],
            "",
            "## Steps To Reproduce",
            data["bug"]["steps"] or "(not provided)",
        ]

        if "logs" in data:
            lines.extend([
                "",
                "## Recent Logs",
                "```text",
            ])
            for log_type, entries in data["logs"].items():
                lines.append(f"[{log_type}]")
                lines.extend(entries[-10:])
            lines.append("```")

        if "config" in data:
            lines.extend([
                "",
                "## Anonymized Config",
                "```json",
                json.dumps(data["config"], indent=2),
                "```",
            ])

        return "\n".join(lines)

    def submit_to_github_browser(self, data):
        destination = self._resolve_github_destination()
        if not destination:
            QMessageBox.warning(
                self,
                "GitHub Destination Missing",
                "Set bug_report.github_repo (owner/repo) in config.json or enter it in the GitHub Destination field.",
            )
            return

        title = f"[{data['bug']['severity']}] {data['bug']['title']}"
        body = self._build_issue_body(data)

        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}
        labels = bug_cfg.get("github_labels", ["bug"])
        if isinstance(labels, list):
            labels_value = ",".join(str(label).strip() for label in labels if str(label).strip())
        else:
            labels_value = str(labels).strip() or "bug"

        assignees = bug_cfg.get("github_assignees", "")
        template = bug_cfg.get("github_template", "")

        final_url = build_browser_issue_url(destination, title, body, labels_value, assignees, template)

        if QDesktopServices.openUrl(QUrl(final_url)):
            QMessageBox.information(
                self,
                "Opening GitHub Issues",
                "A prefilled bug report has been opened in your browser.",
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Open Failed",
                "Could not open the browser for GitHub issue submission.",
            )

    def submit_to_github_api(self, data):
        repo = self._resolve_github_repo()
        if not repo:
            QMessageBox.warning(
                self,
                "GitHub Destination Missing",
                "Set bug_report.github_repo in config.json or enter owner/repo in GitHub Destination.",
            )
            return

        if "/" not in repo:
            QMessageBox.warning(self, "Invalid Repository", "GitHub Destination must be in owner/repo format.")
            return

        token = self._resolve_github_token()
        if not token:
            QMessageBox.warning(
                self,
                "GitHub Token Required",
                "Enter a GitHub token or set bug_report.github_token_env (default GITHUB_TOKEN).",
            )
            return

        title = f"[{data['bug']['severity']}] {data['bug']['title']}"
        body = self._build_issue_body(data)

        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}
        labels = bug_cfg.get("github_labels", ["bug"])
        if isinstance(labels, list):
            labels_list = [str(label).strip() for label in labels if str(label).strip()]
        else:
            labels_list = [part.strip() for part in str(labels).split(",") if part.strip()]

        assignees = bug_cfg.get("github_assignees", "")
        if isinstance(assignees, list):
            assignees_list = [str(a).strip() for a in assignees if str(a).strip()]
        else:
            assignees_list = [part.strip() for part in str(assignees).split(",") if part.strip()]

        payload = {
            "title": title,
            "body": body,
            "labels": labels_list,
        }
        if assignees_list:
            payload["assignees"] = assignees_list

        try:
            response = post_issue_via_api(repo, token, payload)
            if response.status_code in (200, 201):
                response_data = response.json() if response.content else {}
                issue_url = response_data.get("html_url", "")
                QMessageBox.information(
                    self,
                    "Issue Created",
                    f"Bug report created successfully in {repo}.\n\n{issue_url}",
                )
                if issue_url:
                    QDesktopServices.openUrl(QUrl(issue_url))
                self.accept()
                return

            error_message = ""
            try:
                error_message = response.json().get("message", "")
            except Exception:
                error_message = response.text or "Unknown error"
            QMessageBox.warning(
                self,
                "GitHub API Submission Failed",
                f"GitHub API returned {response.status_code}: {error_message}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "GitHub API Error", f"Failed to create issue: {exc}")

    def test_github_connection(self):
        repo = self._resolve_github_repo()
        if not repo or "/" not in repo:
            QMessageBox.warning(self, "Invalid Repository", "GitHub Destination must be in owner/repo format.")
            return

        token = self._resolve_github_token()
        if not token:
            QMessageBox.warning(
                self,
                "GitHub Token Required",
                "Enter a GitHub token or set bug_report.github_token_env (default GITHUB_TOKEN).",
            )
            return

        try:
            success, message, user_login = test_issue_connection(repo, token)
            if success:
                QMessageBox.information(self, "Connection Successful", f"Authenticated as {user_login}.\n{message}")
                return

            QMessageBox.warning(self, "Connection Failed", message)
        except Exception as exc:
            QMessageBox.critical(self, "Connection Error", f"GitHub connection test failed: {exc}")

    def submit_via_email_preview(self, data):
        email = self.email_edit.text().strip()
        if not email:
            QMessageBox.warning(self, "No Email", "Please enter a recipient email address.")
            return

        body = self._build_issue_body(data)
        QMessageBox.information(
            self,
            "Email Preview",
            f"Email would be sent to: {email}\n\nSubject: Bug Report: {data['bug']['title']}\n\nBody preview:\n{body[:800]}...",
        )

    def submit_via_api(self, data):
        if not self.db_manager or not getattr(self.db_manager, "token", None) or not self.config.get("server_url"):
            QMessageBox.warning(self, "Server Not Available", "Server mode is not configured or you are not authenticated.")
            return

        try:
            import requests

            server_url = str(self.config["server_url"]).rstrip("/")
            headers = {"Authorization": f"Bearer {self.db_manager.token}"}
            response = requests.post(f"{server_url}/bug_reports", json=data, headers=headers, timeout=15)
            if response.ok:
                QMessageBox.information(self, "Report Submitted", "Bug report submitted to server successfully.")
                self.accept()
                return

            error_message = response.text or f"Server returned error {response.status_code}."
            QMessageBox.warning(self, "Submission Failed", error_message)
        except Exception as exc:
            QMessageBox.critical(self, "API Error", f"Failed to submit via API: {exc}")

    def save_to_file(self, data):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Bug Report",
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
                body = self._build_issue_body(data)
                with open(file_path, "w", encoding="utf-8") as file_handle:
                    file_handle.write(body)

            QMessageBox.information(self, "Report Saved", f"Bug report saved to {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save report: {exc}")

    def show_log_viewer(self):
        logs = self.collect_logs()
        log_text = ""
        for log_type, lines in logs.items():
            log_text += f"{log_type.upper()}:\n"
            log_text += "\n".join(lines)
            log_text += "\n\n"

        if not log_text.strip():
            QMessageBox.information(self, "No Logs", "No recent logs found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Recent Logs")
        dialog.setMinimumSize(700, 480)
        dialog_layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(log_text)
        dialog_layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        dialog_layout.addWidget(close_btn)

        dialog.exec_()
