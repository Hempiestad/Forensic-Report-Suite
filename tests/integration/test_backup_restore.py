"""Integration tests for backup/restore infrastructure (Phase 3.2c/next).

Covers:
- Local filesystem storage backend behavior
- SQLite backup creation and checksum verification
- SQLite restore (apply + dry-run)
- Tamper detection through checksum mismatch
- PostgreSQL client tool gating behavior (pg_dump/pg_restore missing)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infrastructure.backup.backup_manager import BackupManager
from infrastructure.backup.restore_manager import RestoreManager
from infrastructure.backup.storage_backend import LocalFilesystemStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_sample_sqlite_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sample_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO sample_records(name, value) VALUES ('alpha', 'one')")
        conn.commit()
    finally:
        conn.close()


def _read_sample_value(path: Path) -> str:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("SELECT value FROM sample_records WHERE name = 'alpha'").fetchone()
        assert row is not None
        return str(row[0])
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Storage backend tests
# ---------------------------------------------------------------------------


def test_local_filesystem_storage_roundtrip(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(str(tmp_path / "backup-store"))

    key = "backups/example.bin"
    payload = b"hello-backup"
    storage.write_bytes(key, payload)

    assert storage.exists(key)
    assert storage.read_bytes(key) == payload
    assert key in storage.list_keys("backups")


def test_local_filesystem_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(str(tmp_path / "backup-store"))

    with pytest.raises(ValueError):
        storage.write_bytes("../escape.bin", b"x")


# ---------------------------------------------------------------------------
# SQLite backup/restore tests
# ---------------------------------------------------------------------------


def test_sqlite_backup_and_restore_roundtrip(tmp_path: Path) -> None:
    source_db = tmp_path / "source.db"
    _create_sample_sqlite_db(source_db)

    storage = LocalFilesystemStorage(str(tmp_path / "artifacts"))
    backup_manager = BackupManager(storage)
    restore_manager = RestoreManager(storage)

    metadata = backup_manager.create_sqlite_backup(str(source_db))
    assert metadata.provider == "sqlite"
    assert backup_manager.verify_checksum(metadata.backup_id)

    # Mutate the source DB after backup.
    conn = sqlite3.connect(str(source_db))
    try:
        conn.execute("UPDATE sample_records SET value = 'mutated' WHERE name = 'alpha'")
        conn.commit()
    finally:
        conn.close()

    assert _read_sample_value(source_db) == "mutated"

    # Restore should bring the original value back.
    restore_manager.restore_sqlite_backup(metadata.backup_id, str(source_db))
    assert _read_sample_value(source_db) == "one"


def test_sqlite_restore_dry_run_does_not_modify_target(tmp_path: Path) -> None:
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _create_sample_sqlite_db(source_db)
    _create_sample_sqlite_db(target_db)

    # Change target so we can detect accidental writes.
    conn = sqlite3.connect(str(target_db))
    try:
        conn.execute("UPDATE sample_records SET value = 'target-original' WHERE name = 'alpha'")
        conn.commit()
    finally:
        conn.close()

    storage = LocalFilesystemStorage(str(tmp_path / "artifacts"))
    backup_manager = BackupManager(storage)
    restore_manager = RestoreManager(storage)

    metadata = backup_manager.create_sqlite_backup(str(source_db))
    restore_manager.restore_sqlite_backup(metadata.backup_id, str(target_db), dry_run=True)

    assert _read_sample_value(target_db) == "target-original"


def test_sqlite_restore_fails_on_checksum_mismatch(tmp_path: Path) -> None:
    source_db = tmp_path / "source.db"
    _create_sample_sqlite_db(source_db)

    storage = LocalFilesystemStorage(str(tmp_path / "artifacts"))
    backup_manager = BackupManager(storage)
    restore_manager = RestoreManager(storage)

    metadata = backup_manager.create_sqlite_backup(str(source_db))

    # Tamper artifact bytes after manifest checksum is stored.
    storage.write_bytes(metadata.artifact_key, b"tampered-not-a-sqlite-db")

    with pytest.raises(ValueError, match="Checksum verification failed"):
        restore_manager.restore_sqlite_backup(metadata.backup_id, str(source_db))


def test_sqlite_manifest_is_persisted_and_loadable(tmp_path: Path) -> None:
    source_db = tmp_path / "source.db"
    _create_sample_sqlite_db(source_db)

    storage = LocalFilesystemStorage(str(tmp_path / "artifacts"))
    backup_manager = BackupManager(storage)

    metadata = backup_manager.create_sqlite_backup(str(source_db))
    manifest_key = backup_manager.manifest_key(metadata.backup_id)

    assert storage.exists(manifest_key)

    raw = json.loads(storage.read_bytes(manifest_key).decode("utf-8"))
    assert raw["backup_id"] == metadata.backup_id

    loaded = backup_manager.load_metadata(metadata.backup_id)
    assert loaded.checksum_sha256 == metadata.checksum_sha256


# ---------------------------------------------------------------------------
# PostgreSQL tool-gating tests (no live DB required)
# ---------------------------------------------------------------------------


def test_postgres_backup_raises_when_pg_dump_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = LocalFilesystemStorage(str(tmp_path / "artifacts"))
    backup_manager = BackupManager(storage)

    monkeypatch.setattr("shutil.which", lambda _name: None)

    with pytest.raises(RuntimeError, match="pg_dump not found"):
        backup_manager.create_postgres_backup("postgresql://user:pass@localhost:5432/db")


def test_postgres_restore_raises_when_pg_restore_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_db = tmp_path / "source.db"
    _create_sample_sqlite_db(source_db)

    storage = LocalFilesystemStorage(str(tmp_path / "artifacts"))
    backup_manager = BackupManager(storage)
    restore_manager = RestoreManager(storage)

    # Create a fake postgres backup artifact + manifest directly.
    backup_id = "postgres-test-0001"
    storage.write_bytes(f"backups/{backup_id}.dump", b"fake-pg-dump")
    manifest = {
        "backup_id": backup_id,
        "provider": "postgres",
        "created_at": "2026-01-01T00:00:00",
        "artifact_key": f"backups/{backup_id}.dump",
        "checksum_sha256": backup_manager._sha256(b"fake-pg-dump"),
        "size_bytes": len(b"fake-pg-dump"),
        "source": "postgresql",
        "extra": {},
    }
    storage.write_bytes(backup_manager.manifest_key(backup_id), json.dumps(manifest).encode("utf-8"))

    monkeypatch.setattr("shutil.which", lambda _name: None)

    with pytest.raises(RuntimeError, match="pg_restore not found"):
        restore_manager.restore_postgres_backup(
            backup_id,
            "postgresql://user:pass@localhost:5432/db",
        )
