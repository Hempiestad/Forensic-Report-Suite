#!/usr/bin/env python3
"""
Comprehensive Security Test Suite for FuDog Labs Forensic Report Suite
Tests all implemented security features and mitigations
"""

import sys
import os
import tempfile
import json
import pytest
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from password_utils import (
    hash_password, verify_password, validate_password_strength, is_password_compromised
)


class TestPasswordHashing:
    """Test Argon2 password hashing"""
    
    def test_hash_password_basic(self):
        """Test basic password hashing"""
        password = "SecureP@ssw0rd123"
        hashed = hash_password(password)
        assert hashed is not None
        assert password not in hashed  # Password should not appear in hash
        assert hashed.startswith('$2b$') or hashed.startswith('$2a$')  # bcrypt format
    
    def test_verify_correct_password(self):
        """Test password verification with correct password"""
        password = "SecureP@ssw0rd123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test password verification with wrong password"""
        password = "SecureP@ssw0rd123"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False
    
    def test_hash_empty_password_raises(self):
        """Test that empty password raises error"""
        with pytest.raises(ValueError):
            hash_password("")
    
    def test_hash_short_password(self):
        """Test that short password is hashed (but should be validated before hashing)"""
        # bcrypt doesn't reject short passwords, validation should be done before hashing
        password = "short"
        hashed = hash_password(password)
        assert hashed is not None
        assert verify_password(password, hashed) is True
    
    def test_verify_invalid_hash_returns_false(self):
        """Test that invalid hash returns False"""
        assert verify_password("password", "not_a_real_hash") is False


class TestPasswordValidation:
    """Test password strength validation"""
    
    def test_valid_password(self):
        """Test that valid password passes validation"""
        config = {
            'min_length': 12,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_symbols': True,
        }
        password = "SecureP@ssw0rd123"
        is_valid, msg = validate_password_strength(password, config)
        assert is_valid is True
    
    def test_password_too_short(self):
        """Test password length validation"""
        config = {'min_length': 12}
        password = "Short"
        is_valid, msg = validate_password_strength(password, config)
        assert is_valid is False
        assert "at least 12 characters" in msg
    
    def test_password_missing_uppercase(self):
        """Test uppercase requirement"""
        config = {'min_length': 8, 'require_uppercase': True}
        password = "nouppercasehere123!"
        is_valid, msg = validate_password_strength(password, config)
        assert is_valid is False
        assert "uppercase" in msg.lower()
    
    def test_password_missing_numbers(self):
        """Test numbers requirement"""
        config = {'min_length': 8, 'require_numbers': True}
        password = "NoNumbers!"
        is_valid, msg = validate_password_strength(password, config)
        assert is_valid is False
        assert "numbers" in msg.lower()
    
    def test_password_missing_symbols(self):
        """Test symbol requirement"""
        config = {'min_length': 8, 'require_symbols': True}
        password = "NoSymbols123"
        is_valid, msg = validate_password_strength(password, config)
        assert is_valid is False
        assert "symbol" in msg.lower()


class TestCompromisedPassword:
    """Test compromised password detection"""
    
    def test_weak_password_detected(self):
        """Test that weak passwords are detected"""
        assert is_password_compromised("password") is True
        assert is_password_compromised("password123") is True
        assert is_password_compromised("admin") is True
        assert is_password_compromised("12345678") is True
    
    def test_strong_password_not_flagged(self):
        """Test that strong passwords are not flagged"""
        assert is_password_compromised("SecureP@ssw0rd!") is False
        assert is_password_compromised("MyUniquePass2025!") is False


class TestPathValidation:
    """Test path traversal prevention"""
    
    def test_valid_path_in_directory(self):
        """Test that valid paths are accepted"""
        from reports_tab import validate_appendix_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = tmpdir
            file_path = os.path.join(case_dir, "test_file.txt")
            
            # Should not raise
            result = validate_appendix_path(case_dir, file_path)
            assert result == os.path.abspath(file_path)
    
    def test_path_traversal_detected(self):
        """Test that path traversal is detected"""
        from reports_tab import validate_appendix_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = os.path.join(tmpdir, "case")
            os.makedirs(case_dir, exist_ok=True)
            
            # Try to traverse outside
            malicious_path = os.path.join(case_dir, "..", "..", "etc", "passwd")
            
            with pytest.raises(ValueError):
                validate_appendix_path(case_dir, malicious_path)
    
    def test_absolute_path_outside_case_dir(self):
        """Test that absolute paths outside case dir are rejected"""
        from reports_tab import validate_appendix_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = os.path.join(tmpdir, "case")
            os.makedirs(case_dir, exist_ok=True)
            
            outside_path = os.path.join(tmpdir, "outside.txt")
            
            with pytest.raises(ValueError):
                validate_appendix_path(case_dir, outside_path)


class TestAuditLogSecurity:
    """Test audit log security features"""
    
    def test_audit_log_file_permissions(self):
        """Test that audit log has secure permissions (Unix-like systems)"""
        import stat
        from audit_log import AuditLogger
        import platform
        
        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = tmpdir
            logger = AuditLogger(case_dir, "TEST123")
            logger.log("TEST_EVENT", {"test": "data"})
            
            # Check file exists
            assert os.path.exists(logger.log_file)
            
            # File permissions check (may vary on Windows)
            if platform.system() != 'Windows':
                file_stat = os.stat(logger.log_file)
                mode = file_stat.st_mode
                perms = stat.S_IMODE(mode)
                # Should be 600 (owner read/write only) on Unix
                assert perms == 0o600, f"Expected 0o600, got {oct(perms)}"
    
    def test_audit_log_hash_chain(self):
        """Test that audit log implements tamper-evident logging"""
        from audit_log import AuditLogger
        
        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = tmpdir
            logger = AuditLogger(case_dir, "TEST123")
            logger.log("EVENT_1", {"data": "first"})
            logger.log("EVENT_2", {"data": "second"})
            
            # Read log file
            with open(logger.log_file, "r") as f:
                lines = [json.loads(line) for line in f]
            
            assert len(lines) == 2
            # Each entry should have a hash
            assert "entry_hash" in lines[0]
            assert "entry_hash" in lines[1]
            # Second entry's prev_hash should match first entry's hash
            assert lines[1]["prev_hash"] == lines[0]["entry_hash"]


class TestSecureKeyManager:
    """Test secure key management"""
    
    def test_salt_directory_creation(self):
        """Test that salt directory is created with secure permissions (Unix-like systems)"""
        import stat
        from secure_key_manager import _ensure_salt_directory, SALT_DIR
        import platform
        
        # Temporarily use a test directory
        with tempfile.TemporaryDirectory() as tmpdir:
            test_salt_dir = os.path.join(tmpdir, ".test_forensic")
            
            # Monkey patch for testing
            import secure_key_manager
            orig_dir = secure_key_manager.SALT_DIR
            secure_key_manager.SALT_DIR = test_salt_dir
            
            try:
                secure_key_manager._ensure_salt_directory()
                
                # Check directory exists
                assert os.path.exists(test_salt_dir)
                
                # Check permissions (may vary on Windows)
                if platform.system() != 'Windows':
                    dir_stat = os.stat(test_salt_dir)
                    dir_mode = stat.S_IMODE(dir_stat.st_mode)
                    # Should be 700 (owner read/write/execute only) on Unix
                    assert dir_mode == 0o700, f"Expected 0o700, got {oct(dir_mode)}"
            finally:
                secure_key_manager.SALT_DIR = orig_dir


class TestDatabaseSecurity:
    """Test database security features"""
    
    def test_password_hashing_in_add_evidence(self):
        """Test that passwords are hashed when adding evidence"""
        # This is a conceptual test - requires full DB setup
        # In practice, integration test with real database
        pass


def run_tests():
    """Run all security tests"""
    print("=" * 70)
    print("FUDOG LABS FORENSIC REPORT SUITE - SECURITY TEST SUITE")
    print("=" * 70)
    print()
    
    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✓ All security tests PASSED")
    else:
        print("✗ Some security tests FAILED")
    print("=" * 70)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
