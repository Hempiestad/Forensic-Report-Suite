"""Backup orchestration service for SQLite and PostgreSQL."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from infrastructure.backup.storage_backend import IStorageBackend


@dataclass
class BackupMetadata:
    """Metadata describing a backup artifact."""

    backup_id: str
    provider: str
    created_at: str
    artifact_key: str
    checksum_sha256: str
    size_bytes: int
    source: str
    extra: Dict[str, Any] = field(default_factory=dict)


class BackupManager:
    """Create point-in-time backups and write artifacts to a storage backend."""

    def __init__(self, storage: IStorageBackend) -> None:
        self._storage = storage

    def create_sqlite_backup(self, db_path: str, prefix: str = "sqlite") -> BackupMetadata:
        """Create a SQLite backup using SQLite's online backup API."""
        source = Path(db_path)
        if not source.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")

        backup_id = f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        artifact_key = f"backups/{backup_id}.db"
        manifest_key = self.manifest_key(backup_id)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            tmp_backup_path = Path(tmp_file.name)

        try:
            src_conn = sqlite3.connect(str(source))
            dst_conn = sqlite3.connect(str(tmp_backup_path))
            try:
                src_conn.backup(dst_conn)
                dst_conn.commit()
            finally:
                dst_conn.close()
                src_conn.close()

            content = tmp_backup_path.read_bytes()
            checksum = self._sha256(content)

            metadata = BackupMetadata(
                backup_id=backup_id,
                provider="sqlite",
                created_at=datetime.utcnow().isoformat(),
                artifact_key=artifact_key,
                checksum_sha256=checksum,
                size_bytes=len(content),
                source=str(source),
            )
            self._storage.write_bytes(artifact_key, content)
            self._storage.write_bytes(manifest_key, json.dumps(asdict(metadata), indent=2).encode("utf-8"))
            return metadata
        finally:
            if tmp_backup_path.exists():
                tmp_backup_path.unlink()

    def create_postgres_backup(self, dsn: str, prefix: str = "postgres") -> BackupMetadata:
        """Create a PostgreSQL logical backup using pg_dump custom format."""
        pg_dump = shutil.which("pg_dump")
        if pg_dump is None:
            raise RuntimeError("pg_dump not found in PATH. Install PostgreSQL client tools.")

        backup_id = f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        artifact_key = f"backups/{backup_id}.dump"
        manifest_key = self.manifest_key(backup_id)

        cmd = [
            pg_dump,
            "--dbname",
            dsn,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--verbose",
        ]

        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"pg_dump failed (exit={result.returncode}): {stderr}")

        content = result.stdout
        checksum = self._sha256(content)
        metadata = BackupMetadata(
            backup_id=backup_id,
            provider="postgres",
            created_at=datetime.utcnow().isoformat(),
            artifact_key=artifact_key,
            checksum_sha256=checksum,
            size_bytes=len(content),
            source="postgresql",
            extra={"dsn_redacted": self._redact_dsn(dsn)},
        )

        self._storage.write_bytes(artifact_key, content)
        self._storage.write_bytes(manifest_key, json.dumps(asdict(metadata), indent=2).encode("utf-8"))
        return metadata

    def load_metadata(self, backup_id: str) -> BackupMetadata:
        """Load a backup manifest and deserialize into BackupMetadata."""
        content = self._storage.read_bytes(self.manifest_key(backup_id))
        payload = json.loads(content.decode("utf-8"))
        return BackupMetadata(**payload)

    def verify_checksum(self, backup_id: str) -> bool:
        """Validate backup artifact checksum against its manifest."""
        md = self.load_metadata(backup_id)
        content = self._storage.read_bytes(md.artifact_key)
        return self._sha256(content) == md.checksum_sha256

    @staticmethod
    def manifest_key(backup_id: str) -> str:
        return f"backups/{backup_id}.manifest.json"

    @staticmethod
    def _sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _redact_dsn(dsn: str) -> str:
        # Replace credentials in DSN user:password@ with user:***@.
        return re.sub(r"(?<=://[^:/?#\s]+):[^@\s]+@", ":***@", dsn, count=1)
