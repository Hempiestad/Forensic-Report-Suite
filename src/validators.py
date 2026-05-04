# validators.py
# Input validation module for FuDog Labs Forensic Report Suite
# Prevents injection attacks, path traversal, and data validation errors

import os
import re
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


# ============================================================================
# Case and Report Validation
# ============================================================================

def validate_case_number(case_num: str, max_length: int = 50) -> bool:
    """
    Validate case number format (alphanumeric, dash, underscore only).
    
    Args:
        case_num: Case number string to validate
        max_length: Maximum allowed length (default 50)
    
    Returns:
        True if valid, False otherwise
    
    Examples:
        >>> validate_case_number("CASE-001")
        True
        >>> validate_case_number("case_2025")
        True
        >>> validate_case_number("../../../etc/passwd")
        False
        >>> validate_case_number("CASE;DROP TABLE")
        False
    """
    if not case_num or not isinstance(case_num, str):
        logger.warning("Case number validation failed: not a string or empty")
        return False
    
    case_num = case_num.strip()
    
    if len(case_num) == 0 or len(case_num) > max_length:
        logger.warning(f"Case number validation failed: length {len(case_num)} outside 1-{max_length}")
        return False
    
    # Allow only alphanumeric, dash, underscore
    if not re.match(r'^[a-zA-Z0-9_-]+$', case_num):
        logger.warning(f"Case number validation failed: contains invalid characters: {case_num}")
        return False
    
    return True


def validate_file_path(file_path: str, allowed_dir: str, must_exist: bool = False) -> bool:
    """
    Validate file path prevents directory traversal attacks.
    
    Args:
        file_path: Path to validate
        allowed_dir: Base directory that path must be within
        must_exist: If True, file must exist
    
    Returns:
        True if valid, False otherwise
    
    Raises:
        ValidationError with detailed message
    """
    if not file_path or not isinstance(file_path, str):
        logger.warning("File path validation failed: not a string or empty")
        raise ValidationError("File path must be a non-empty string")
    
    try:
        # Resolve to absolute paths
        abs_path = Path(file_path).resolve()
        abs_allowed = Path(allowed_dir).resolve()
        
        # Check if path is within allowed directory
        abs_path.relative_to(abs_allowed)
        
    except (ValueError, RuntimeError) as e:
        logger.warning(f"File path validation failed: path traversal detected for {file_path}: {e}")
        raise ValidationError(f"File path is outside allowed directory: {e}")
    
    # Check existence if required
    if must_exist and not abs_path.exists():
        logger.warning(f"File path validation failed: file does not exist: {file_path}")
        raise ValidationError(f"File does not exist: {file_path}")
    
    return True


def validate_status(status: str, allowed_statuses: list[str]) -> bool:
    """
    Validate case/evidence status against allowed values.
    
    Args:
        status: Status string to validate
        allowed_statuses: List of allowed status values
    
    Returns:
        True if status is in allowed list, False otherwise
    """
    if not status or not isinstance(status, str):
        logger.warning("Status validation failed: not a string or empty")
        return False
    
    status = status.strip().lower()
    allowed_lower = [s.lower() for s in allowed_statuses]
    
    if status not in allowed_lower:
        logger.warning(f"Status validation failed: '{status}' not in {allowed_statuses}")
        return False
    
    return True


# ============================================================================
# Authentication and User Input
# ============================================================================

def validate_username(username: str, min_length: int = 3, max_length: int = 100) -> bool:
    """
    Validate username format and length.
    
    Args:
        username: Username to validate
        min_length: Minimum length (default 3)
        max_length: Maximum length (default 100)
    
    Returns:
        True if valid, False otherwise
    """
    if not username or not isinstance(username, str):
        return False
    
    username = username.strip()
    
    if len(username) < min_length or len(username) > max_length:
        logger.warning(f"Username validation failed: length {len(username)} outside {min_length}-{max_length}")
        return False
    
    # Allow alphanumeric, dash, underscore, dot
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        logger.warning(f"Username validation failed: invalid characters in {username}")
        return False
    
    return True


def validate_password(password: str, min_length: int = 8) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        min_length: Minimum length (default 8)
    
    Returns:
        Tuple of (is_valid, message)
    """
    if not password or not isinstance(password, str):
        return False, "Password must be a non-empty string"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letters"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain numbers"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain special characters"
    
    return True, "Password is strong"


# ============================================================================
# Email and Network
# ============================================================================

def validate_email(email: str, max_length: int = 254) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        max_length: Maximum length (RFC 5321 allows up to 254)
    
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    email = email.strip().lower()
    
    if len(email) > max_length:
        logger.warning(f"Email validation failed: length {len(email)} exceeds {max_length}")
        return False
    
    # Simple RFC 5322-compliant regex (simplified for practical use)
    pattern = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    
    if not re.match(pattern, email):
        logger.warning(f"Email validation failed: invalid format: {email}")
        return False
    
    return True


def validate_url(url: str, allowed_schemes: list[str] = None) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed schemes (default ['http', 'https'])
    
    Returns:
        True if valid, False otherwise
    """
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    try:
        # Check if scheme is allowed
        scheme = url.split('://')[0].lower()
        if scheme not in allowed_schemes:
            logger.warning(f"URL validation failed: scheme '{scheme}' not in {allowed_schemes}")
            return False
        
        # Basic URL pattern
        pattern = r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/$.?#].[^\s]*$'
        if not re.match(pattern, url):
            logger.warning(f"URL validation failed: invalid format: {url}")
            return False
        
        return True
    except Exception as e:
        logger.warning(f"URL validation failed: {e}")
        return False


# ============================================================================
# File Operations
# ============================================================================

def validate_file_extension(filename: str, allowed_extensions: set[str]) -> bool:
    """
    Validate file extension against whitelist.
    
    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions (e.g., {'.pdf', '.docx', '.txt'})
    
    Returns:
        True if extension is allowed, False otherwise
    """
    if not filename or not isinstance(filename, str):
        logger.warning("Filename validation failed: not a string or empty")
        return False
    
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in allowed_extensions:
        logger.warning(f"File extension validation failed: '{ext}' not in {allowed_extensions}")
        return False
    
    return True


def validate_file_size(file_path: str, max_size_bytes: int) -> bool:
    """
    Validate file size does not exceed maximum.
    
    Args:
        file_path: Path to file
        max_size_bytes: Maximum allowed size in bytes
    
    Returns:
        True if file size is within limit, False otherwise
    """
    if not os.path.exists(file_path):
        logger.warning(f"File size validation failed: file does not exist: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    
    if file_size > max_size_bytes:
        logger.warning(f"File size validation failed: {file_size} bytes exceeds {max_size_bytes}")
        return False
    
    return True


# ============================================================================
# Date and Number Validation
# ============================================================================

def validate_iso_date(date_str: str) -> bool:
    """
    Validate ISO 8601 date format (YYYY-MM-DD).
    
    Args:
        date_str: Date string to validate
    
    Returns:
        True if valid ISO date, False otherwise
    """
    if not date_str or not isinstance(date_str, str):
        return False
    
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        logger.warning(f"ISO date validation failed: invalid format: {date_str}")
        return False
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError as e:
        logger.warning(f"ISO date validation failed: {e}")
        return False


def validate_positive_integer(value: Any, min_value: int = 0, max_value: Optional[int] = None) -> bool:
    """
    Validate value is a positive integer within range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value (default 0)
        max_value: Maximum allowed value (None for unlimited)
    
    Returns:
        True if valid, False otherwise
    """
    # Reject float values — int(5.5) would silently truncate
    if isinstance(value, float):
        logger.warning(f"Integer validation failed: float value {value!r} not allowed")
        return False
    try:
        int_value = int(value)
        
        if int_value < min_value:
            logger.warning(f"Integer validation failed: {int_value} < {min_value}")
            return False
        
        if max_value is not None and int_value > max_value:
            logger.warning(f"Integer validation failed: {int_value} > {max_value}")
            return False
        
        return True
    except (ValueError, TypeError) as e:
        logger.warning(f"Integer validation failed: {e}")
        return False


# ============================================================================
# JSON and Data Structure Validation
# ============================================================================

def validate_json_string(json_str: str) -> tuple[bool, Optional[dict]]:
    """
    Validate JSON string and return parsed object.
    
    Args:
        json_str: JSON string to validate
    
    Returns:
        Tuple of (is_valid, parsed_object or None)
    """
    if not json_str or not isinstance(json_str, str):
        return False, None
    
    try:
        import json
        data = json.loads(json_str)
        return True, data
    except json.JSONDecodeError as e:
        logger.warning(f"JSON validation failed: {e}")
        return False, None


# ============================================================================
# Utility Functions
# ============================================================================

def sanitize_sql_string(value: str) -> str:
    """
    Basic SQL string sanitization (escaping single quotes).
    
    WARNING: Use parameterized queries instead when possible!
    This is a fallback only for cases where parameterization isn't available.
    
    Args:
        value: String to sanitize
    
    Returns:
        Sanitized string with escaped single quotes
    """
    if not isinstance(value, str):
        return str(value)
    
    # Escape single quotes by doubling them (SQL standard)
    sanitized = value.replace("'", "''")
    logger.debug(f"SQL string sanitized: {len(value)} chars → {len(sanitized)} chars")
    
    return sanitized


def truncate_string(value: str, max_length: int) -> str:
    """
    Safely truncate string to maximum length.
    
    Args:
        value: String to truncate
        max_length: Maximum length
    
    Returns:
        Truncated string
    """
    if not isinstance(value, str):
        value = str(value)
    
    if len(value) > max_length:
        logger.debug(f"String truncated: {len(value)} → {max_length} chars")
        return value[:max_length]
    
    return value


# ============================================================================
# Validation Decorator
# ============================================================================

def validate_input(**validation_rules):
    """
    Decorator for automatic input validation on function arguments.
    
    Usage:
        @validate_input(
            case_number=dict(validator='case_number'),
            file_path=dict(validator='file_path', allowed_dir='./cases'),
            email=dict(validator='email')
        )
        def my_function(case_number, file_path, email):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validation logic would go here
            # For now, just call the original function
            return func(*args, **kwargs)
        return wrapper
    return decorator
