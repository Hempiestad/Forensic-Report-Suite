"""Integration tests for Phase 3.2c — Encrypted Audit Trail.

Validates:
- AES-256-GCM encrypt/decrypt round-trip on AuditEncryptionManager
- Tamper detection (GCM authentication tag rejects modified ciphertext)
- Key vault: InMemoryKeyVault works; EnvironmentKeyVault reads env var correctly
- SQLiteAuditRepository encrypts details on write and decrypts on read
- Hash chain integrity is preserved when encryption is enabled
- Backward-compat: repo without encryption_manager reads plaintext rows fine
- Encrypted repo can read back rows it wrote (round-trip via reload)
- generate_key() / key_to_env_string() helpers work
- PostgreSQL equivalents (env-gated)
"""
from __future__ import annotations

import base64
import json
import os
import tempfile
from typing import Any, Dict

import pytest

FORENSIC_PG_DSN = os.getenv("FORENSIC_PG_DSN")
_skip_pg = pytest.mark.skipif(not FORENSIC_PG_DSN, reason="FORENSIC_PG_DSN not set")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(key: bytes | None = None):
    """Return an AuditEncryptionManager backed by an InMemoryKeyVault."""
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager
    from infrastructure.encryption.key_vault import InMemoryKeyVault

    if key is None:
        key = AuditEncryptionManager.generate_key()
    vault = InMemoryKeyVault({"audit-v1": key})
    return AuditEncryptionManager(vault, key_id="audit-v1"), key


def _sqlite_ctx(path: str | None = None):
    from infrastructure.persistence.db_context import SQLiteDbContext

    if path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        path = tmp.name
    return SQLiteDbContext(path)


# ---------------------------------------------------------------------------
# AuditEncryptionManager unit tests
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_roundtrip() -> None:
    """Encrypting and decrypting a details dict returns the original."""
    mgr, _ = _make_manager()
    original = {"action": "report_saved", "user": "alice", "count": 42}

    encrypted = mgr.encrypt_details(original)
    assert mgr.is_encrypted(encrypted)
    assert "__enc" in encrypted
    assert "nonce" in encrypted
    assert "ct" in encrypted

    decrypted = mgr.decrypt_details(encrypted)
    assert decrypted == original


def test_encrypted_payload_is_opaque() -> None:
    """Ciphertext does not contain plaintext values."""
    mgr, _ = _make_manager()
    details = {"secret": "top-secret-evidence", "case": "XYZ-999"}

    encrypted = mgr.encrypt_details(details)
    ct_b64 = encrypted["ct"]
    ct_bytes = base64.urlsafe_b64decode(ct_b64 + "==")

    assert b"top-secret-evidence" not in ct_bytes
    assert b"XYZ-999" not in ct_bytes


def test_tamper_detection_raises() -> None:
    """Modifying the ciphertext raises ValueError (GCM tag mismatch)."""
    mgr, _ = _make_manager()
    encrypted = mgr.encrypt_details({"x": 1})

    # Flip a byte in the ciphertext
    ct_bytes = bytearray(base64.urlsafe_b64decode(encrypted["ct"] + "=="))
    ct_bytes[0] ^= 0xFF
    tampered = dict(encrypted)
    tampered["ct"] = base64.urlsafe_b64encode(bytes(ct_bytes)).decode("ascii")

    with pytest.raises(ValueError, match="decryption failed"):
        mgr.decrypt_details(tampered)


def test_wrong_key_raises() -> None:
    """Decrypting with a different key raises ValueError."""
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager
    from infrastructure.encryption.key_vault import InMemoryKeyVault

    key_a = AuditEncryptionManager.generate_key()
    key_b = AuditEncryptionManager.generate_key()

    mgr_a = AuditEncryptionManager(InMemoryKeyVault({"audit-v1": key_a}))
    mgr_b = AuditEncryptionManager(InMemoryKeyVault({"audit-v1": key_b}))

    encrypted = mgr_a.encrypt_details({"x": 1})
    with pytest.raises(ValueError):
        mgr_b.decrypt_details(encrypted)


def test_decrypt_plaintext_dict_returns_unchanged() -> None:
    """decrypt_details on a non-encrypted dict returns it unchanged (backward-compat)."""
    mgr, _ = _make_manager()
    plaintext = {"action": "old_row", "legacy": True}

    result = mgr.decrypt_details(plaintext)
    assert result == plaintext


def test_is_encrypted_false_for_plaintext() -> None:
    """is_encrypted returns False for a plain dict without __enc."""
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager

    assert not AuditEncryptionManager.is_encrypted({"action": "login"})
    assert not AuditEncryptionManager.is_encrypted({})
    assert not AuditEncryptionManager.is_encrypted({"__enc": False})


def test_generate_key_length() -> None:
    """generate_key produces 32 bytes (256-bit)."""
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager

    key = AuditEncryptionManager.generate_key()
    assert len(key) == 32


def test_key_to_env_string_roundtrip() -> None:
    """key_to_env_string encodes a key that EnvironmentKeyVault can decode."""
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager
    from infrastructure.encryption.key_vault import EnvironmentKeyVault

    key = AuditEncryptionManager.generate_key()
    env_str = AuditEncryptionManager.key_to_env_string(key)

    os.environ["_TEST_AUDIT_KEY"] = env_str
    try:
        vault = EnvironmentKeyVault(default_env_var="_TEST_AUDIT_KEY", default_key_id="test-key")
        retrieved = vault.get_key("test-key")
        assert retrieved == key
    finally:
        del os.environ["_TEST_AUDIT_KEY"]


# ---------------------------------------------------------------------------
# Key vault tests
# ---------------------------------------------------------------------------

def test_inmemory_vault_missing_key_raises() -> None:
    from infrastructure.encryption.key_vault import InMemoryKeyVault

    vault = InMemoryKeyVault({"k1": b"\x00" * 32})
    with pytest.raises(KeyError):
        vault.get_key("k2")


def test_env_vault_missing_env_var_raises() -> None:
    from infrastructure.encryption.key_vault import EnvironmentKeyVault

    vault = EnvironmentKeyVault(default_env_var="__NONEXISTENT_ENV_VAR_XYZ__")
    with pytest.raises(KeyError, match="not set"):
        vault.get_key("audit-v1")


def test_env_vault_wrong_key_length_raises() -> None:
    from infrastructure.encryption.key_vault import EnvironmentKeyVault

    # 16-byte key (AES-128) instead of 32 (AES-256)
    short_key = base64.urlsafe_b64encode(b"\x00" * 16).decode()
    os.environ["_TEST_SHORT_KEY"] = short_key
    try:
        vault = EnvironmentKeyVault(default_env_var="_TEST_SHORT_KEY")
        with pytest.raises(ValueError, match="16 bytes"):
            vault.get_key("audit-v1")
    finally:
        del os.environ["_TEST_SHORT_KEY"]


# ---------------------------------------------------------------------------
# SQLite encrypted repository tests
# ---------------------------------------------------------------------------

def test_sqlite_encrypted_repo_stores_ciphertext() -> None:
    """Raw SQLite row contains encrypted payload, not plaintext details."""
    from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
    from domain.entities.audit_entry import AuditEntry

    mgr, _ = _make_manager()
    ctx = _sqlite_ctx()
    try:
        repo = SQLiteAuditRepository(ctx, encryption_manager=mgr)

        entry = AuditEntry.create(
            case_number="ENC-001",
            event_type="CASE_CREATED",
            performed_by="alice",
            details={"evidence": "top-secret", "location": "lab-3"},
        )
        repo.add(entry)
        ctx.commit()

        # Read raw from DB — should NOT contain plaintext
        raw = ctx.connection.execute(
            "SELECT details FROM audit_entries WHERE case_number = 'ENC-001'"
        ).fetchone()
        raw_details = json.loads(raw["details"])

        assert raw_details.get("__enc") is True, "Expected encrypted payload in DB"
        assert "evidence" not in json.dumps(raw_details), "Plaintext leaked into storage"
    finally:
        ctx.close()


def test_sqlite_encrypted_repo_roundtrip() -> None:
    """Writing and reading back an encrypted entry returns original details."""
    from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
    from domain.entities.audit_entry import AuditEntry

    mgr, _ = _make_manager()
    ctx = _sqlite_ctx()
    try:
        repo = SQLiteAuditRepository(ctx, encryption_manager=mgr)

        entry = AuditEntry.create(
            case_number="ENC-002",
            event_type="REPORT_SAVED",
            performed_by="bob",
            details={"report_id": 42, "status": "FINAL"},
        )
        repo.add(entry)
        ctx.commit()

        loaded = repo.get_by_id(str(entry.id))
        assert loaded is not None
        assert loaded.details == {"report_id": 42, "status": "FINAL"}
    finally:
        ctx.close()


def test_sqlite_encrypted_chain_integrity() -> None:
    """Hash chain integrity holds when all entries are encrypted."""
    from application.services.audit_service import AuditService
    from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository

    mgr, _ = _make_manager()
    ctx = _sqlite_ctx()
    try:
        repo = SQLiteAuditRepository(ctx, encryption_manager=mgr)
        svc = AuditService(repo)

        for i in range(5):
            svc.log("CHAIN-001", "EVENT", "tester", {"step": i, "secret": f"data-{i}"})
        ctx.commit()

        assert svc.verify_chain_integrity("CHAIN-001"), "Chain integrity broken with encryption"
    finally:
        ctx.close()


def test_sqlite_encrypted_repo_backward_compat_plaintext_rows() -> None:
    """An encrypted repo can read back rows that were written without encryption."""
    from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
    from domain.entities.audit_entry import AuditEntry

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    # Write without encryption
    ctx_plain = _sqlite_ctx(tmp.name)
    repo_plain = SQLiteAuditRepository(ctx_plain)
    entry = AuditEntry.create(
        case_number="LEGACY-001",
        event_type="LOGIN",
        performed_by="legacy_user",
        details={"source": "plaintext"},
    )
    repo_plain.add(entry)
    ctx_plain.commit()
    ctx_plain.close()

    # Read with encryption enabled — should still load the plaintext row
    mgr, _ = _make_manager()
    ctx_enc = _sqlite_ctx(tmp.name)
    repo_enc = SQLiteAuditRepository(ctx_enc, encryption_manager=mgr)
    loaded = repo_enc.get_by_id(str(entry.id))
    assert loaded is not None
    assert loaded.details == {"source": "plaintext"}, "Backward-compat load failed"
    ctx_enc.close()


def test_sqlite_no_encryption_plaintext_stored() -> None:
    """Without encryption_manager, details are stored as plaintext JSON."""
    from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
    from domain.entities.audit_entry import AuditEntry

    ctx = _sqlite_ctx()
    try:
        repo = SQLiteAuditRepository(ctx)  # no encryption

        entry = AuditEntry.create(
            case_number="PLAIN-001",
            event_type="SEARCH",
            performed_by="charlie",
            details={"query": "murder weapon"},
        )
        repo.add(entry)
        ctx.commit()

        raw = ctx.connection.execute(
            "SELECT details FROM audit_entries WHERE case_number = 'PLAIN-001'"
        ).fetchone()
        parsed = json.loads(raw["details"])
        assert parsed == {"query": "murder weapon"}
    finally:
        ctx.close()


def test_sqlite_encrypted_get_for_case_decrypts_all() -> None:
    """get_for_case returns decrypted entries for all rows."""
    from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
    from domain.entities.audit_entry import AuditEntry

    mgr, _ = _make_manager()
    ctx = _sqlite_ctx()
    try:
        repo = SQLiteAuditRepository(ctx, encryption_manager=mgr)

        for i in range(3):
            e = AuditEntry.create(
                case_number="MULTI-001",
                event_type=f"EVENT_{i}",
                performed_by="dave",
                details={"index": i},
            )
            repo.add(e)
        ctx.commit()

        entries = repo.get_for_case("MULTI-001")
        assert len(entries) == 3
        for i, e in enumerate(entries):
            assert e.details == {"index": i}
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# PostgreSQL encrypted repository tests (env-gated)
# ---------------------------------------------------------------------------

@_skip_pg
def test_postgres_encrypted_repo_roundtrip() -> None:
    """PostgreSQLAuditRepository encrypts/decrypts details correctly."""
    from infrastructure.persistence.db_context import PostgreSQLDbContext
    from infrastructure.persistence.repositories.postgres_audit_repository import PostgreSQLAuditRepository
    from domain.entities.audit_entry import AuditEntry

    mgr, _ = _make_manager()
    with PostgreSQLDbContext(FORENSIC_PG_DSN) as ctx:  # type: ignore[arg-type]
        repo = PostgreSQLAuditRepository(ctx, encryption_manager=mgr)

        entry = AuditEntry.create(
            case_number="PG-ENC-001",
            event_type="CASE_CREATED",
            performed_by="pg_alice",
            details={"pg_secret": "classified", "priority": "HIGH"},
        )
        repo.add(entry)
        ctx.commit()

        loaded = repo.get_by_id(str(entry.id))
        assert loaded is not None
        assert loaded.details == {"pg_secret": "classified", "priority": "HIGH"}

        # Cleanup
        repo.delete(str(entry.id))
        ctx.commit()


@_skip_pg
def test_postgres_encrypted_chain_integrity() -> None:
    """Hash chain integrity holds for PostgreSQL encrypted audit entries."""
    from application.services.audit_service import AuditService
    from infrastructure.persistence.db_context import PostgreSQLDbContext
    from infrastructure.persistence.repositories.postgres_audit_repository import PostgreSQLAuditRepository

    mgr, _ = _make_manager()
    with PostgreSQLDbContext(FORENSIC_PG_DSN) as ctx:  # type: ignore[arg-type]
        repo = PostgreSQLAuditRepository(ctx, encryption_manager=mgr)
        svc = AuditService(repo)

        for i in range(4):
            svc.log("PG-CHAIN-001", "EVENT", "pg_tester", {"step": i})
        ctx.commit()

        assert svc.verify_chain_integrity("PG-CHAIN-001")

        # Cleanup
        for e in repo.get_for_case("PG-CHAIN-001"):
            repo.delete(str(e.id))
        ctx.commit()
