# auth.py
import json
import os
import re
import logging
from ldap3 import Server, Connection, NTLM
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QLabel, QPushButton, QMessageBox, QDialogButtonBox

logger = logging.getLogger(__name__)

# Input validation constants
_USERNAME_MAX_LEN = 100
_PASSWORD_MAX_LEN = 256
# Allow alphanumeric, dot, hyphen, underscore, @ for domain accounts
_USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9._@\-]+$')


def validate_credentials(username: str, password: str) -> str | None:
    """Validate username and password inputs. Returns an error message string, or None if valid."""
    if not username:
        return "Username is required."
    if len(username) > _USERNAME_MAX_LEN:
        return f"Username must not exceed {_USERNAME_MAX_LEN} characters."
    if not _USERNAME_PATTERN.match(username):
        return "Username contains invalid characters."
    if not password:
        return "Password is required."
    if len(password) > _PASSWORD_MAX_LEN:
        return f"Password must not exceed {_PASSWORD_MAX_LEN} characters."
    return None

CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from config.json with safe defaults."""
    default_config = {
        "use_ad": False,
        "server_url": "",
        "ad_server": "",
        "ad_domain": "",
        "ad_base_dn": ""
    }

    if not os.path.exists(CONFIG_FILE):
        return default_config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        default_config.update(user_config)
        return default_config
    except Exception as e:
        logger.warning(f"Could not load config.json ({e}). Using defaults.")
        return default_config

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)

        layout = QFormLayout(self)

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        layout.addRow("Username:", self.username_edit)
        layout.addRow("Password:", self.password_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_credentials(self):
        return self.username_edit.text().strip(), self.password_edit.text()

def authenticate():
    cfg = load_config()

    # Standalone mode: no login required
    if not cfg.get("use_ad") and not cfg.get("server_url"):
        return {"username": "anonymous", "role": "admin"}

    # Show login dialog
    dialog = LoginDialog()
    if dialog.exec_() != QDialog.Accepted:
        return None

    username, password = dialog.get_credentials()
    error = validate_credentials(username, password)
    if error:
        QMessageBox.warning(None, "Login", error)
        return None

    # If server_url is configured, use server for authentication
    if cfg.get("server_url"):
        try:
            import requests
            resp = requests.post(
                f"{cfg['server_url'].rstrip('/')}/login",
                json={"username": username, "password": password},
                timeout=10
            )
            if resp.ok:
                data = resp.json()
                return {
                    "username": username,
                    "role": data.get("role", "writer"),
                    "token": data.get("token")
                }
            else:
                QMessageBox.critical(None, "Login Failed", resp.text or "Invalid credentials")
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", f"Cannot reach server:\n{e}")
        return None

    # Pure AD mode
    if cfg.get("use_ad"):
        try:
            server = Server(cfg['ad_server'], get_info=ALL)
            conn = Connection(
                server,
                user=f"{cfg['ad_domain']}\\{username}",
                password=password,
                authentication=NTLM
            )
            if conn.bind():
                return {"username": username, "role": "writer"}  # Role assigned on server in enterprise
            else:
                QMessageBox.critical(None, "Login Failed", "Invalid AD credentials")
        except Exception as e:
            QMessageBox.critical(None, "AD Error", f"Authentication failed:\n{e}")
        return None

    return None