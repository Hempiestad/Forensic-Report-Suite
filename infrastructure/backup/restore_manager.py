"""Restore orchestration service for backup artifacts."""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from infrastructure.backup.backup_manager import BackupManager, BackupMetadata
from infrastructure.backup.storage_backend import IStorageBackend


class RestoreManager:
    """Restore backup artifacts created by BackupManager."""

    def __init__(self, storage: IStorageBackend) -> None:
        self._storage = storage
        self._backup_manager = BackupManager(storage)

    def restore_sqlite_backup(self, backup_id: str, target_db_path: str, dry_run: bool = False) -> BackupMetadata:
        """Restore a SQLite backup to a target path.

        If dry_run is True, validate checksum + integrity without writing target.
        """
        metadata = self._backup_manager.load_metadata(backup_id)
        if metadata.provider != "sqlite":
            raise ValueError(f"Backup '{backup_id}' is not a SQLite backup.")
        if not self._backup_manager.verify_checksum(backup_id):
            raise ValueError(f"Checksum verification failed for backup '{backup_id}'.")

        content = self._storage.read_bytes(metadata.artifact_key)

        # Always run integrity check before final restore.
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        try:
            tmp_path.write_bytes(content)
            self._validate_sqlite_integrity(str(tmp_path))

            if dry_run:
                return metadata

            target = Path(target_db_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir=str(target.parent)) as staged:
                staged_path = Path(staged.name)
            staged_path.write_bytes(content)
            staged_path.replace(target)
            return metadata
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def restore_postgres_backup(self, backup_id: str, dsn: str, dry_run: bool = False, clean: bool = False) -> BackupMetadata:
        """Restore a PostgreSQL logical backup using pg_restore."""
        metadata = self._backup_manager.load_metadata(backup_id)
        if metadata.provider != "postgres":
            raise ValueError(f"Backup '{backup_id}' is not a PostgreSQL backup.")
        if not self._backup_manager.verify_checksum(backup_id):
            raise ValueError(f"Checksum verification failed for backup '{backup_id}'.")

        pg_restore = shutil.which("pg_restore")
        if pg_restore is None:
            raise RuntimeError("pg_restore not found in PATH. Install PostgreSQL client tools.")

        content = self._storage.read_bytes(metadata.artifact_key)
        with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        try:
            if dry_run:
                # Validate dump archive readability without applying changes.
                cmd = [pg_restore, "--list", str(tmp_path)]
                result = subprocess.run(cmd, capture_output=True, check=False)
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="ignore")
                    raise RuntimeError(f"pg_restore --list failed (exit={result.returncode}): {stderr}")
                return metadata

            cmd = [pg_restore, "--dbname", dsn, "--single-transaction", "--verbose"]
            if clean:
                cmd.extend(["--clean", "--if-exists"])
            cmd.append(str(tmp_path))
            result = subprocess.run(cmd, capture_output=True, check=False)
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="ignore")
                raise RuntimeError(f"pg_restore failed (exit={result.returncode}): {stderr}")
            return metadata
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @staticmethod
    def _validate_sqlite_integrity(path: str) -> None:
        conn = sqlite3.connect(path)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if not row or str(row[0]).lower() != "ok":
                raise ValueError(f"SQLite integrity_check failed: {row}")
        finally:
            conn.close()
