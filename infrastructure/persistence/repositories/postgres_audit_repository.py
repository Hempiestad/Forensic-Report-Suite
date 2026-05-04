"""PostgreSQL-backed audit repository implementation."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from application.interfaces.i_audit_repository import IAuditRepository
from domain.entities.audit_entry import AuditEntry
from infrastructure.persistence.db_context import PostgreSQLDbContext

if TYPE_CHECKING:
    from infrastructure.encryption.audit_encryption import AuditEncryptionManager


class PostgreSQLAuditRepository(IAuditRepository):
    """Concrete PostgreSQL adapter for audit persistence.

    Args:
        db_context:          PostgreSQL database context.
        encryption_manager:  Optional AuditEncryptionManager.  When provided,
                             the ``details`` dict is AES-256-GCM encrypted
                             before being written and decrypted on read.
                             Existing plaintext JSONB rows continue to load
                             correctly (backward-compatible).
    """

    def __init__(
        self,
        db_context: PostgreSQLDbContext,
        encryption_manager: Optional["AuditEncryptionManager"] = None,
    ) -> None:
        self._db = db_context
        self._enc = encryption_manager

    def get_by_id(self, entity_id: str) -> Optional[AuditEntry]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM audit_entries WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[AuditEntry]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM audit_entries ORDER BY timestamp ASC, id ASC")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: AuditEntry) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_entries (
                    case_number, event_type, performed_by, details, timestamp, previous_hash, entry_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    entity.case_number,
                    entity.event_type,
                    entity.performed_by,
                    json.dumps(self._serialise_details(entity.details)),
                    entity.timestamp,
                    entity.previous_hash,
                    entity.entry_hash,
                ),
            )
            row = cur.fetchone()
        if row:
            entity.id = int(row["id"])

    def update(self, entity: AuditEntry) -> None:
        if entity.id is None:
            return
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE audit_entries
                SET case_number = %s,
                    event_type = %s,
                    performed_by = %s,
                    details = %s,
                    timestamp = %s,
                    previous_hash = %s,
                    entry_hash = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.event_type,
                    entity.performed_by,
                    json.dumps(self._serialise_details(entity.details)),
                    entity.timestamp,
                    entity.previous_hash,
                    entity.entry_hash,
                    int(entity.id),
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM audit_entries WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM audit_entries WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> List[AuditEntry]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM audit_entries WHERE case_number = %s ORDER BY timestamp ASC, id ASC",
                (case_number,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM audit_entries ORDER BY timestamp DESC, id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_last_entry_for_case(self, case_number: str) -> Optional[AuditEntry]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM audit_entries WHERE case_number = %s ORDER BY timestamp DESC, id DESC LIMIT 1",
                (case_number,),
            )
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _serialise_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt details dict if an encryption manager is configured."""
        if self._enc is not None:
            return self._enc.encrypt_details(details)
        return details

    def _deserialise_details(self, raw) -> Dict[str, Any]:
        """Decrypt details if the stored payload is encrypted."""
        # psycopg3 returns JSONB columns as Python dicts already
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return {}
        if raw is None:
            return {}
        enc = getattr(self, "_enc", None)
        if enc is not None and enc.is_encrypted(raw):
            return enc.decrypt_details(raw)
        return raw

    def _to_entity(self, row) -> AuditEntry:
        return AuditEntry(
            id=int(row["id"]) if row["id"] is not None else None,
            case_number=row["case_number"],
            event_type=row["event_type"],
            performed_by=row["performed_by"],
            details=self._deserialise_details(row["details"]),
            timestamp=row["timestamp"],
            previous_hash=row["previous_hash"],
            entry_hash=row["entry_hash"],
        )
