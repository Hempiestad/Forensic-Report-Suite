# password_utils.py - Secure password hashing and validation

import re
import os
import bcrypt

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with high security parameters.

    Args:
        password: Plain text password to hash

    Returns:
        bcrypt hash string (safe to store in database)

    Raises:
        ValueError: If password is invalid
    """
    if not password or len(password) < 1:
        raise ValueError("Password cannot be empty")

    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hash_str: str) -> bool:
    """
    Verify a password against its bcrypt hash.

    Args:
        password: Plain text password to verify
        hash_str: bcrypt hash string from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hash_str.encode('utf-8'))
    except (TypeError, ValueError):
        return False


def validate_password_strength(password: str, config: dict = None) -> tuple[bool, str]:
    """
    Validate password meets security requirements.
    
    Args:
        password: Password to validate
        config: Optional dict with validation rules:
            - min_length: minimum password length (default 12)
            - require_uppercase: require A-Z (default True)
            - require_lowercase: require a-z (default True)
            - require_numbers: require 0-9 (default True)
            - require_symbols: require !@#$%^&* (default True)
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if config is None:
        config = {}
    
    # Set defaults for missing keys
    config.setdefault('min_length', int(os.getenv('PASSWORD_MIN_LENGTH', 12)))
    config.setdefault('require_uppercase', os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'True').lower() == 'true')
    config.setdefault('require_lowercase', True)
    config.setdefault('require_numbers', os.getenv('PASSWORD_REQUIRE_NUMBERS', 'True').lower() == 'true')
    config.setdefault('require_symbols', os.getenv('PASSWORD_REQUIRE_SYMBOLS', 'True').lower() == 'true')
    
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < config['min_length']:
        return False, f"Password must be at least {config['min_length']} characters"
    
    if config['require_lowercase'] and not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letters (a-z)"
    
    if config['require_uppercase'] and not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letters (A-Z)"
    
    if config['require_numbers'] and not re.search(r'[0-9]', password):
        return False, "Password must contain numbers (0-9)"
    
    if config['require_symbols'] and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Password must contain symbols (!@#$%^&*)"
    
    return True, "Password meets requirements"


def is_password_compromised(password: str) -> bool:
    """
    Check if password is in known compromised password list (offline).
    This is a simple local check. For production, integrate with Have I Been Pwned API.
    
    Args:
        password: Password to check
        
    Returns:
        True if password appears in common compromised passwords, False otherwise
    """
    # Common weak passwords to block
    weak_passwords = {
        'password', 'password123', 'admin', 'admin123', '12345678',
        'qwerty', 'letmein', 'welcome', 'monkey', 'dragon'
    }
    return password.lower() in weak_passwords
