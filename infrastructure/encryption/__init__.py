"""
infrastructure/encryption/ — Encryption service implementations (Phase 3).

Modules:
    key_vault         — IKeyVault protocol + InMemoryKeyVault + EnvironmentKeyVault
    audit_encryption  — AES-256-GCM AuditEncryptionManager for audit details
"""
from infrastructure.encryption.key_vault import (
    EnvironmentKeyVault,
    IKeyVault,
    InMemoryKeyVault,
)
from infrastructure.encryption.audit_encryption import AuditEncryptionManager

__all__ = [
    "IKeyVault",
    "InMemoryKeyVault",
    "EnvironmentKeyVault",
    "AuditEncryptionManager",
]
