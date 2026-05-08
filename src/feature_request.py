# feature_request.py
# Feature Request Dialog for FuDog Labs Forensic Report Suite

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


class FeatureRequestDialog(QDialog):
    KEYRING_SERVICE = "ForensicReportSuite"
    KEYRING_USERNAME = "github_issue_api"

    def __init__(self, parent=None, current_user=None, db_manager=None):
        super().__init__(parent)
        self.current_user = current_user or {"username": "anonymous", "role": "user"}
        self.db_manager = db_manager
        self.config = self.load_config()

        self.setWindowTitle("Request New Feature")
        self.setMinimumSize(640, 480)
        self.resize(760, 600)
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

        title_label = QLabel("Request a Feature")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        intro_label = QLabel(
            "Describe the outcome you want and the problem it solves. "
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
        self.description_edit.setMinimumHeight(120)
        details_layout.addRow("Description:", self.description_edit)

        self.benefits_edit = QTextEdit()
        self.benefits_edit.setPlaceholderText("What problem does this solve or what benefit would it provide?")
        self.benefits_edit.setMinimumHeight(90)
        details_layout.addRow("Benefits:", self.benefits_edit)

        self.use_cases_edit = QTextEdit()
        self.use_cases_edit.setPlaceholderText("Add one or more examples of how this feature would be used...")
        self.use_cases_edit.setMinimumHeight(90)
        details_layout.addRow("Use Cases:", self.use_cases_edit)

        layout.addWidget(details_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
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

        feature_cfg = self.config.get("feature_request", {}) if isinstance(self.config, dict) else {}
        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}

        self.github_destination_edit = QLineEdit()
        self.github_destination_edit.setPlaceholderText("owner/repo or full GitHub issue URL")
        self.github_destination_edit.setText(
            str(
                feature_cfg.get("github_repo")
                or bug_cfg.get("github_repo")
                or feature_cfg.get("github_issues_url")
                or ""
            )
        )
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
        self.email_edit.setText(str(feature_cfg.get("email") or self.config.get("feature_request_email", "")))
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
        self.submit_btn = QPushButton("Submit Request")
        self.submit_btn.clicked.connect(self.submit_request)
        button_layout.addWidget(self.submit_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        outer_layout.addLayout(button_layout)

        self.initialize_submission_mode()

    def initialize_submission_mode(self):
        if bool(self.config.get("server_url")) if isinstance(self.config, dict) else False:
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
            "Server API": "Sends the request to the configured application server if server mode is available.",
            "Save to File": "Exports the request content locally as JSON or plain text.",
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
        config_copy = dict(self.config) if isinstance(self.config, dict) else {}
        sensitive_keys = [
            "ad_server",
            "ad_domain",
            "ad_base_dn",
            "server_url",
            "feature_request_email",
            "bug_report_email",
            "github_token",
        ]

        redact_config_sections(config_copy, ["feature_request", "bug_report"])

        for key in sensitive_keys:
            if key in config_copy:
                config_copy[key] = "[REDACTED]"

        return config_copy

    def submit_request(self):
        data = self.collect_request_data()
        if not data["feature"]["title"] or not data["feature"]["description"]:
            QMessageBox.warning(self, "Incomplete Request", "Please fill in at least the title and description.")
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

        feature_cfg = self.config.get("feature_request", {}) if isinstance(self.config, dict) else {}
        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}
        return str(
            feature_cfg.get("github_repo")
            or bug_cfg.get("github_repo")
            or feature_cfg.get("github_issues_url")
            or ""
        ).strip()

    def _get_github_token_from_keyring(self):
        if keyring is None:
            return ""

        try:
            token = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME)
        except Exception:
            return ""
        return str(token or "").strip()

    def _resolve_github_token(self):
        typed = self.github_token_edit.text().strip()
        if typed:
            return typed

        # Share the same secure token store used by the bug reporting dialog.
        keyring_token = self._get_github_token_from_keyring()
        if keyring_token:
            return keyring_token

        feature_cfg = self.config.get("feature_request", {}) if isinstance(self.config, dict) else {}
        bug_cfg = self.config.get("bug_report", {}) if isinstance(self.config, dict) else {}
        env_var_name = str(
            feature_cfg.get("github_token_env")
            or bug_cfg.get("github_token_env")
            or "GITHUB_TOKEN"
        ).strip() or "GITHUB_TOKEN"
        env_token = os.environ.get(env_var_name, "").strip()
        if env_token:
            return env_token

        return str(feature_cfg.get("github_token", "") or bug_cfg.get("github_token", "")).strip()

    def _resolve_github_repo(self):
        return resolve_repo_from_destination(self._resolve_github_destination())

    def _build_issue_body(self, data):
        lines = [
            "## Feature Request",
            f"- Priority: {data['feature']['priority']}",
            f"- User: {data['user']['username']} ({data['user']['role']})",
            f"- Timestamp: {data['timestamp']}",
            f"- System: {data['system']['os']}",
            f"- Python: {data['system']['python']}",
            f"- PyQt5: {data['system']['pyqt5']}",
            "",
            "## Description",
            data["feature"]["description"],
            "",
            "## Benefits",
            data["feature"]["benefits"] or "(not provided)",
            "",
            "## Use Cases",
            data["feature"]["use_cases"] or "(not provided)",
        ]

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
                "Set feature_request.github_repo in config.json or enter owner/repo in GitHub Destination.",
            )
            return

        title = f"[Feature] {data['feature']['title']}"
        body = self._build_issue_body(data)

        feature_cfg = self.config.get("feature_request", {}) if isinstance(self.config, dict) else {}
        labels = feature_cfg.get("github_labels", ["enhancement"])
        if isinstance(labels, list):
            labels_value = ",".join(str(label).strip() for label in labels if str(label).strip())
        else:
            labels_value = str(labels).strip() or "enhancement"

        assignees = feature_cfg.get("github_assignees", "")
        template = feature_cfg.get("github_template", "")

        final_url = build_browser_issue_url(destination, title, body, labels_value, assignees, template)

        if QDesktopServices.openUrl(QUrl(final_url)):
            QMessageBox.information(self, "Opening GitHub Issues", "A prefilled feature request has been opened in your browser.")
            self.accept()
        else:
            QMessageBox.warning(self, "Open Failed", "Could not open the browser for GitHub feature request submission.")

    def submit_to_github_api(self, data):
        repo = self._resolve_github_repo()
        if not repo:
            QMessageBox.warning(
                self,
                "GitHub Destination Missing",
                "Set feature_request.github_repo in config.json or enter owner/repo in GitHub Destination.",
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
                "Enter a GitHub token or configure GITHUB_TOKEN for direct feature request submission.",
            )
            return

        title = f"[Feature] {data['feature']['title']}"
        body = self._build_issue_body(data)

        feature_cfg = self.config.get("feature_request", {}) if isinstance(self.config, dict) else {}
        labels = feature_cfg.get("github_labels", ["enhancement"])
        if isinstance(labels, list):
            labels_list = [str(label).strip() for label in labels if str(label).strip()]
        else:
            labels_list = [part.strip() for part in str(labels).split(",") if part.strip()]

        assignees = feature_cfg.get("github_assignees", "")
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
                    "Request Created",
                    f"Feature request created successfully in {repo}.\n\n{issue_url}",
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
            QMessageBox.critical(self, "GitHub API Error", f"Failed to create feature request: {exc}")

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
                "Enter a GitHub token or configure GITHUB_TOKEN for direct feature request submission.",
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
            f"Email would be sent to: {email}\n\nSubject: Feature Request: {data['feature']['title']}\n\nBody preview:\n{body[:800]}...",
        )

    def submit_via_api(self, data):
        if not self.db_manager or not getattr(self.db_manager, "token", None) or not self.config.get("server_url"):
            QMessageBox.warning(self, "Server Not Available", "Server mode is not configured or you are not authenticated.")
            return

        try:
            import requests

            server_url = str(self.config["server_url"]).rstrip("/")
            headers = {"Authorization": f"Bearer {self.db_manager.token}"}
            response = requests.post(f"{server_url}/feature_requests", json=data, headers=headers, timeout=15)
            if response.ok:
                QMessageBox.information(self, "Request Submitted", "Feature request submitted to server successfully.")
                self.accept()
                return

            error_message = response.text or f"Server returned error {response.status_code}."
            QMessageBox.warning(self, "Submission Failed", error_message)
        except Exception as exc:
            QMessageBox.critical(self, "API Error", f"Failed to submit the feature request: {exc}")

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
                    file_handle.write(self._build_issue_body(data))

            QMessageBox.information(self, "Request Saved", f"Feature request saved to {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save request: {exc}")
