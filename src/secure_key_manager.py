# secure_key_manager.py
import os
import keyring
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QLineEdit
import base64
import getpass
import stat

SERVICE_NAME = "SecureForensicReportWriter"
USERNAME = "master_key"  # Fixed username in keyring

# Secure salt storage location
SALT_DIR = os.path.expanduser("~/.forensic_app")
SALT_FILE = os.path.join(SALT_DIR, "salt.bin")

def derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """
    Derive encryption key from passphrase using PBKDF2-SHA256.
    Uses high iteration count (600,000) for security against brute force.
    """
    if not passphrase:
        raise ValueError("Passphrase cannot be empty")
    if len(passphrase) < 8:
        raise ValueError("Passphrase must be at least 8 characters")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,  # High iteration count for security
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode('utf-8')))


def _ensure_salt_directory():
    """Create salt directory with secure permissions (700)."""
    try:
        os.makedirs(SALT_DIR, mode=0o700, exist_ok=True)
        # Ensure directory permissions are correct
        os.chmod(SALT_DIR, 0o700)
    except Exception as e:
        raise RuntimeError(f"Failed to create secure salt directory: {e}")


def _load_or_create_salt() -> bytes:
    """Load existing salt or create new one with secure permissions."""
    _ensure_salt_directory()
    
    if os.path.exists(SALT_FILE):
        try:
            with open(SALT_FILE, "rb") as f:
                salt = f.read()
            if len(salt) != 16:
                raise ValueError("Invalid salt file (incorrect length)")
            return salt
        except Exception as e:
            raise ValueError(f"Cannot read salt file: {e}")
    else:
        # Create new salt
        salt = os.urandom(16)
        try:
            # Write with secure permissions (600 - owner read/write only)
            with open(SALT_FILE, "wb") as f:
                f.write(salt)
            os.chmod(SALT_FILE, 0o600)  # Restrict to owner only
        except Exception as e:
            raise RuntimeError(f"Failed to write salt file: {e}")
        return salt

def get_or_create_cipher():
    """
    Get or create encryption cipher.
    Uses system keyring for key storage and interactive passphrase prompt.
    """
    # Try to get key from system keyring first
    stored_key = keyring.get_password(SERVICE_NAME, USERNAME)
    
    if stored_key:
        try:
            # Test if key works (we store a small test token)
            test_token = keyring.get_password(SERVICE_NAME, "test_token")
            Fernet(stored_key.encode()).decrypt(test_token.encode())
            return Fernet(stored_key.encode())
        except (InvalidToken, TypeError):
            # Key corrupted or wrong — fall back to passphrase prompt
            keyring.delete_password(SERVICE_NAME, USERNAME)
            keyring.delete_password(SERVICE_NAME, "test_token")

    # No valid key in keyring → ask user for passphrase (first time or recovery)
    max_attempts = 3
    for attempt in range(max_attempts):
        passphrase, ok = QInputDialog.getText(
            None, 
            "Encryption Passphrase Required",
            "Enter your master passphrase\n(Used to encrypt sensitive data):",
            QLineEdit.Password
        )
        if not ok:
            QMessageBox.critical(None, "Error", "Passphrase required to continue.")
            raise SystemExit("No passphrase provided")
        
        if not passphrase:
            QMessageBox.warning(None, "Error", "Passphrase cannot be empty")
            continue
        
        if len(passphrase) < 8:
            QMessageBox.warning(None, "Error", "Passphrase must be at least 8 characters")
            continue
        
        break
    else:
        raise SystemExit("Maximum passphrase attempts exceeded")

    try:
        # Load or create salt securely
        salt = _load_or_create_salt()
        
        # Derive encryption key
        key = derive_key_from_passphrase(passphrase, salt)
        cipher = Fernet(key)
        
        # Store in keyring for future use
        keyring.set_password(SERVICE_NAME, USERNAME, key.decode())
        
        # Store test token to validate future loads
        test_token = cipher.encrypt(b"key_valid")
        keyring.set_password(SERVICE_NAME, "test_token", test_token.decode())
        
        # Clear passphrase from memory
        del passphrase
        
        QMessageBox.information(
            None, 
            "Key Setup Complete",
            "Encryption key securely configured using your passphrase.\n"
            "It is now stored in the system keychain.\n"
            "Salt file stored in: " + SALT_DIR
        )
        
        return cipher
        
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to set up encryption: {str(e)}")
        raise SystemExit(f"Encryption setup failed: {e}")

# Global cipher instance - lazy loaded to avoid QWidget creation before QApplication
CIPHER = None

def get_cipher():
    global CIPHER
    if CIPHER is None:
        CIPHER = get_or_create_cipher()
    return CIPHER

def encrypt_data(data: str) -> bytes:
    return get_cipher().encrypt(data.encode('utf-8'))

def decrypt_data(token: bytes) -> str:
    try:
        return get_cipher().decrypt(token).decode('utf-8')
    except InvalidToken:
        raise ValueError("Invalid passphrase or corrupted data")
