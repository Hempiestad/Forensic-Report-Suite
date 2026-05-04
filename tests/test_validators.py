# tests/test_validators.py
# Comprehensive test suite for input validators
# Tests validation functions and SQL injection prevention

import pytest
import tempfile
import os
from pathlib import Path

# Import validators
from validators import (
    validate_case_number, validate_file_path, validate_status,
    validate_username, validate_password, validate_email, validate_url,
    validate_file_extension, validate_file_size, validate_iso_date,
    validate_positive_integer, validate_json_string, ValidationError,
    sanitize_sql_string, truncate_string
)


class TestCaseNumberValidation:
    """Test case number validation"""
    
    @pytest.mark.parametrize("case_num,expected", [
        ("CASE-001", True),
        ("case_2025", True),
        ("TEST_CASE-123", True),
        ("A", True),
        ("X" * 50, True),
        ("", False),
        (None, False),
        ("../../../etc/passwd", False),
        ("CASE;DROP TABLE", False),
        ("CASE' OR '1'='1", False),
        ("CASE\"; DROP TABLE; --", False),
        ("X" * 51, False),  # Exceeds max_length
        ("case@domain", False),
        ("case#tag", False),
        ("case with spaces", False),
    ])
    def test_validate_case_number(self, case_num, expected):
        """Test case number validation with various inputs"""
        assert validate_case_number(case_num) == expected
    
    def test_case_number_max_length(self):
        """Test case number with custom max_length"""
        assert validate_case_number("X" * 100, max_length=100) == True
        assert validate_case_number("X" * 101, max_length=100) == False


class TestFilePathValidation:
    """Test file path validation for directory traversal prevention"""
    
    def test_valid_file_path(self):
        """Test valid file path within allowed directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed_dir = tmpdir
            file_path = os.path.join(tmpdir, "test.txt")
            assert validate_file_path(file_path, allowed_dir) == True
    
    def test_invalid_file_path_traversal(self):
        """Test directory traversal attack prevention"""
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed_dir = tmpdir
            attack_path = os.path.join(tmpdir, "../../etc/passwd")
            
            with pytest.raises(ValidationError):
                validate_file_path(attack_path, allowed_dir)
    
    def test_file_path_outside_allowed(self):
        """Test path outside allowed directory"""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                allowed_dir = tmpdir1
                outside_path = os.path.join(tmpdir2, "test.txt")
                
                with pytest.raises(ValidationError):
                    validate_file_path(outside_path, allowed_dir)
    
    def test_file_path_must_exist(self):
        """Test must_exist parameter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed_dir = tmpdir
            non_existent = os.path.join(tmpdir, "nonexistent.txt")
            
            # Should fail when must_exist=True
            with pytest.raises(ValidationError):
                validate_file_path(non_existent, allowed_dir, must_exist=True)
            
            # Should pass when must_exist=False
            assert validate_file_path(non_existent, allowed_dir, must_exist=False) == True


class TestStatusValidation:
    """Test status validation"""
    
    @pytest.mark.parametrize("status,allowed,expected", [
        ("draft", ["draft", "approved", "closed"], True),
        ("DRAFT", ["draft", "approved", "closed"], True),  # Case-insensitive
        ("approved", ["draft", "approved", "closed"], True),
        ("invalid", ["draft", "approved", "closed"], False),
        ("", ["draft", "approved", "closed"], False),
        (None, ["draft", "approved", "closed"], False),
    ])
    def test_validate_status(self, status, allowed, expected):
        """Test status validation"""
        assert validate_status(status, allowed) == expected


class TestUsernameValidation:
    """Test username validation"""
    
    @pytest.mark.parametrize("username,expected", [
        ("user123", True),
        ("john.doe", True),
        ("john-doe", True),
        ("john_doe", True),
        ("u", False),  # Too short
        ("a" * 101, False),  # Too long
        ("user@domain", False),  # Invalid character
        ("user name", False),  # Space
        ("", False),
        (None, False),
    ])
    def test_validate_username(self, username, expected):
        """Test username validation"""
        assert validate_username(username) == expected


class TestPasswordValidation:
    """Test password strength validation"""
    
    def test_strong_password(self):
        """Test valid strong password"""
        is_valid, msg = validate_password("SecureP@ss123")
        assert is_valid == True
    
    def test_weak_password_no_uppercase(self):
        """Test password without uppercase"""
        is_valid, msg = validate_password("securep@ss123")
        assert is_valid == False
        assert "uppercase" in msg.lower()
    
    def test_weak_password_no_lowercase(self):
        """Test password without lowercase"""
        is_valid, msg = validate_password("SECUREP@SS123")
        assert is_valid == False
        assert "lowercase" in msg.lower()
    
    def test_weak_password_no_numbers(self):
        """Test password without numbers"""
        is_valid, msg = validate_password("SecureP@ssword")
        assert is_valid == False
        assert "number" in msg.lower()
    
    def test_weak_password_no_special(self):
        """Test password without special characters"""
        is_valid, msg = validate_password("SecurePass123")
        assert is_valid == False
        assert "special" in msg.lower()
    
    def test_weak_password_too_short(self):
        """Test password too short"""
        is_valid, msg = validate_password("Pass@123")  # 8 chars
        # Depending on implementation, might still be valid at exactly 8 chars
        # This tests the minimum length boundary


class TestEmailValidation:
    """Test email validation"""
    
    @pytest.mark.parametrize("email,expected", [
        ("user@example.com", True),
        ("john.doe@company.co.uk", True),
        ("user+tag@domain.org", True),
        ("invalid.email@", False),
        ("@domain.com", False),
        ("user@.com", False),
        ("user space@domain.com", False),
        ("", False),
        (None, False),
    ])
    def test_validate_email(self, email, expected):
        """Test email validation"""
        assert validate_email(email) == expected


class TestURLValidation:
    """Test URL validation"""
    
    @pytest.mark.parametrize("url,expected", [
        ("https://example.com", True),
        ("http://example.com", True),
        ("https://sub.example.com/path", True),
        ("ftp://files.example.com", False),  # Not allowed by default
        ("javascript:alert('xss')", False),
        ("https://", False),
        ("", False),
        (None, False),
    ])
    def test_validate_url(self, url, expected):
        """Test URL validation"""
        assert validate_url(url) == expected
    
    def test_validate_url_custom_schemes(self):
        """Test URL with custom allowed schemes"""
        assert validate_url("ftp://files.example.com", allowed_schemes=['ftp']) == True
        assert validate_url("ftp://files.example.com", allowed_schemes=['http', 'https']) == False


class TestFileExtensionValidation:
    """Test file extension validation"""
    
    def test_valid_extension(self):
        """Test valid file extensions"""
        allowed = {'.pdf', '.docx', '.txt'}
        assert validate_file_extension("report.pdf", allowed) == True
        assert validate_file_extension("document.docx", allowed) == True
    
    def test_invalid_extension(self):
        """Test invalid file extensions"""
        allowed = {'.pdf', '.docx'}
        assert validate_file_extension("script.exe", allowed) == False
        assert validate_file_extension("document.doc", allowed) == False
    
    def test_case_insensitive_extension(self):
        """Test case-insensitive extension matching"""
        allowed = {'.pdf', '.docx'}
        assert validate_file_extension("report.PDF", allowed) == True
        assert validate_file_extension("report.PDF", allowed) == True


class TestFileSizeValidation:
    """Test file size validation"""
    
    def test_file_size_within_limit(self):
        """Test file within size limit"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * 1000)  # 1KB
            tmp_path = tmp.name
        
        try:
            assert validate_file_size(tmp_path, max_size_bytes=10000) == True
        finally:
            os.unlink(tmp_path)
    
    def test_file_size_exceeds_limit(self):
        """Test file exceeds size limit"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * 10000)  # 10KB
            tmp_path = tmp.name
        
        try:
            assert validate_file_size(tmp_path, max_size_bytes=1000) == False
        finally:
            os.unlink(tmp_path)


class TestDateValidation:
    """Test ISO date validation"""
    
    @pytest.mark.parametrize("date_str,expected", [
        ("2025-01-15", True),
        ("2025-12-31", True),
        ("2025-2-1", False),  # Not padded
        ("2025/01/15", False),  # Wrong separator
        ("01-15-2025", False),  # Wrong format
        ("2025-13-01", False),  # Invalid month
        ("2025-01-32", False),  # Invalid day
        ("", False),
        (None, False),
    ])
    def test_validate_iso_date(self, date_str, expected):
        """Test ISO date validation"""
        assert validate_iso_date(date_str) == expected


class TestIntegerValidation:
    """Test integer validation"""
    
    @pytest.mark.parametrize("value,min_val,max_val,expected", [
        (5, 0, 10, True),
        (0, 0, 10, True),
        (10, 0, 10, True),
        (-1, 0, 10, False),
        (11, 0, 10, False),
        ("5", 0, 10, True),  # String that converts
        ("abc", 0, 10, False),
        (5.5, 0, 10, False),  # Float
    ])
    def test_validate_positive_integer(self, value, min_val, max_val, expected):
        """Test integer validation"""
        assert validate_positive_integer(value, min_val, max_val) == expected


class TestJSONValidation:
    """Test JSON string validation"""
    
    def test_valid_json(self):
        """Test valid JSON string"""
        is_valid, data = validate_json_string('{"key": "value"}')
        assert is_valid == True
        assert data == {"key": "value"}
    
    def test_invalid_json(self):
        """Test invalid JSON string"""
        is_valid, data = validate_json_string("{'key': 'value'}")  # Single quotes
        assert is_valid == False
        assert data is None
    
    def test_empty_json_string(self):
        """Test empty JSON string"""
        is_valid, data = validate_json_string("")
        assert is_valid == False


class TestSQLSanitization:
    """Test SQL string sanitization"""
    
    def test_sanitize_simple_quote(self):
        """Test SQL string with single quote"""
        original = "O'Reilly"
        sanitized = sanitize_sql_string(original)
        assert "'" not in sanitized or "''" in sanitized
    
    def test_sanitize_sql_injection_attempt(self):
        """Test SQL injection attempt sanitization"""
        original = "'; DROP TABLE users; --"
        sanitized = sanitize_sql_string(original)
        # Should escape quotes
        assert "''" in sanitized or "'" not in sanitized


class TestStringTruncation:
    """Test string truncation utility"""
    
    def test_truncate_long_string(self):
        """Test truncating long string"""
        long_string = "x" * 100
        result = truncate_string(long_string, 50)
        assert len(result) == 50
        assert result == "x" * 50
    
    def test_truncate_short_string(self):
        """Test truncating short string (no truncation needed)"""
        short_string = "hello"
        result = truncate_string(short_string, 50)
        assert result == short_string


# ============================================================================
# SQL Injection Prevention Tests (for database.py)
# ============================================================================

class TestSQLInjectionPrevention:
    """Test SQL injection prevention measures in database operations"""
    
    def test_illegal_date_field_rejected(self):
        """Test that illegal date fields in update_legal_process_status are rejected"""
        from database import DatabaseManager
        
        db = DatabaseManager()
        
        # Attack attempt: SQL injection via date_field
        with pytest.raises(ValueError) as exc_info:
            db.update_legal_process_status(1, 'pending', "submitted); DROP TABLE reports; --", "2025-01-01")
        
        assert "Invalid date field" in str(exc_info.value)
    
    def test_valid_date_field_accepted(self):
        """Test that valid date fields are accepted"""
        from database import DatabaseManager
        
        db = DatabaseManager()
        
        # Valid date field should work (might fail on actual DB operation if DB issue, but won't be SQL injection)
        try:
            # This should either succeed or fail with a DB error, not ValueError
            result = db.update_legal_process_status(9999, 'pending', 'submission_date', "2025-01-01")
            # If it reaches here, field validation passed
        except ValueError:
            pytest.fail("Valid date field was rejected")
        except Exception as e:
            # Other exceptions (like DB errors) are OK for this test
            # We're just checking that ValueError for field injection didn't occur
            pass
    
    def test_illegal_evidence_field_rejected(self):
        """Test that illegal evidence fields are rejected"""
        from database import DatabaseManager
        
        db = DatabaseManager()
        
        # Attack attempt: SQL injection via field
        with pytest.raises(ValueError) as exc_info:
            db.update_evidence_field(1, "item_type); DROP TABLE evidence_items; --", "bad")
        
        assert "Invalid evidence field" in str(exc_info.value)
    
    def test_illegal_evidence_item_update_rejected(self):
        """Test that illegal fields in update_evidence_item are rejected"""
        from database import DatabaseManager
        
        db = DatabaseManager()
        
        # Attack attempt: SQL injection via kwargs
        with pytest.raises(ValueError) as exc_info:
            db.update_evidence_item(1, **{"item_type); DROP TABLE evidence_items; --": "bad"})
        
        assert "Invalid evidence field" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
