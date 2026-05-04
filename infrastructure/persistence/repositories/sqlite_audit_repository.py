"""SQLite-backed audit repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from application.interfaces.i_audit_repository import IAuditRepository
from domain.entities.audit_entry import AuditEntry
from infrastructure.persistence.db_context import SQLiteDbContext

if TYPE_CHECKING:
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager


class SQLiteAuditRepository(IAuditRepository):
    """Concrete SQLite adapter for audit persistence.

    Args:
        db_context:          SQLite database context.
        encryption_manager:  Optional AuditEncryptionManager.  When provided,
                             the ``details`` dict is AES-256-GCM encrypted
                             before being written and decrypted on read.
                             Existing plaintext rows continue to load correctly
                             (backward-compatible).
    """

    def __init__(
        self,
        db_context: SQLiteDbContext,
        encryption_manager: Optional["AuditEncryptionManager"] = None,
    ) -> None:
        self._db = db_context
        self._enc = encryption_manager

    def get_by_id(self, entity_id: str) -> Optional[AuditEntry]:
        row = self._db.connection.execute("SELECT * FROM audit_entries WHERE id = ?", (int(entity_id),)).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[AuditEntry]:
        rows = self._db.connection.execute("SELECT * FROM audit_entries ORDER BY timestamp ASC, id ASC").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: AuditEntry) -> None:
        cursor = self._db.connection.execute(
            """
            INSERT INTO audit_entries (case_number, event_type, performed_by, details, timestamp, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.case_number,
                entity.event_type,
                entity.performed_by,
                self._serialise_details(entity.details),
                entity.timestamp.isoformat(),
                entity.previous_hash,
                entity.entry_hash,
            ),
        )
        entity.id = int(cursor.lastrowid)

    def update(self, entity: AuditEntry) -> None:
        if entity.id is None:
            return
        self._db.connection.execute(
            """
            UPDATE audit_entries
            SET case_number = ?, event_type = ?, performed_by = ?, details = ?,
                timestamp = ?, previous_hash = ?, entry_hash = ?
            WHERE id = ?
            """,
            (
                entity.case_number,
                entity.event_type,
                entity.performed_by,
                self._serialise_details(entity.details),
                entity.timestamp.isoformat(),
                entity.previous_hash,
                entity.entry_hash,
                int(entity.id),
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM audit_entries WHERE id = ?", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute("SELECT 1 FROM audit_entries WHERE id = ? LIMIT 1", (int(entity_id),)).fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> List[AuditEntry]:
        rows = self._db.connection.execute(
            "SELECT * FROM audit_entries WHERE case_number = ? ORDER BY timestamp ASC, id ASC",
            (case_number,),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        rows = self._db.connection.execute(
            "SELECT * FROM audit_entries ORDER BY timestamp DESC, id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_last_entry_for_case(self, case_number: str) -> Optional[AuditEntry]:
        row = self._db.connection.execute(
            "SELECT * FROM audit_entries WHERE case_number = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (case_number,),
        ).fetchone()
        return self._to_entity(row) if row else None

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _serialise_details(self, details: dict) -> str:
        """Serialise details to JSON, encrypting if an encryption manager is set."""
        if self._enc is not None:
            return json.dumps(self._enc.encrypt_details(details))
        return json.dumps(details)

    def _deserialise_details(self, raw: Optional[str]) -> dict:
        """Parse stored details JSON, decrypting if the payload is encrypted."""
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        if self._enc is not None and self._enc.is_encrypted(parsed):
            return self._enc.decrypt_details(parsed)
        return parsed

    def _to_entity(self, row) -> AuditEntry:
        timestamp = datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.utcnow()
        return AuditEntry(
            id=int(row["id"]) if row["id"] is not None else None,
            case_number=row["case_number"],
            event_type=row["event_type"],
            performed_by=row["performed_by"],
            details=self._deserialise_details(row["details"]),
            timestamp=timestamp,
            previous_hash=row["previous_hash"],
            entry_hash=row["entry_hash"],
        )
