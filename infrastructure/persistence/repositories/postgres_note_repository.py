"""PostgreSQL-backed Note repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_note_repository import INoteRepository
from domain.entities.note import Note
from domain.enums.note_status import NoteStatus
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLNoteRepository(INoteRepository):
    """Concrete PostgreSQL adapter for Note persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    # ------------------------------------------------------------------ #
    # IRepository                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, entity_id: str) -> Optional[Note]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM notes WHERE id = %s", (entity_id,))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Note]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM notes ORDER BY created_at")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Note) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notes (id, case_number, title, body, created_by,
                                   created_at, modified_at, modified_by,
                                   status, tags, note_type, priority,
                                   approved_by, approved_at, approval_comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entity.id,
                    entity.case_number,
                    entity.title,
                    entity.body,
                    entity.created_by,
                    entity.created_at or datetime.utcnow(),
                    entity.modified_at,
                    entity.modified_by,
                    entity.status.value if entity.status else NoteStatus.ACTIVE.value,
                    json.dumps(entity.tags),
                    entity.note_type,
                    entity.priority,
                    entity.approved_by,
                    entity.approved_at,
                    entity.approval_comments,
                ),
            )

    def update(self, entity: Note) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE notes
                SET case_number       = %s,
                    title             = %s,
                    body              = %s,
                    created_by        = %s,
                    created_at        = %s,
                    modified_at       = %s,
                    modified_by       = %s,
                    status            = %s,
                    tags              = %s,
                    note_type         = %s,
                    priority          = %s,
                    approved_by       = %s,
                    approved_at       = %s,
                    approval_comments = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.title,
                    entity.body,
                    entity.created_by,
                    entity.created_at or datetime.utcnow(),
                    entity.modified_at,
                    entity.modified_by,
                    entity.status.value if entity.status else NoteStatus.ACTIVE.value,
                    json.dumps(entity.tags),
                    entity.note_type,
                    entity.priority,
                    entity.approved_by,
                    entity.approved_at,
                    entity.approval_comments,
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s", (entity_id,))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM notes WHERE id = %s LIMIT 1", (entity_id,))
            row = cur.fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # INoteRepository                                                      #
    # ------------------------------------------------------------------ #

    def get_for_case(self, case_number: str) -> List[Note]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM notes WHERE case_number = %s AND status = %s ORDER BY created_at",
                (case_number, NoteStatus.ACTIVE.value),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def search(self, query: str, case_number: Optional[str] = None) -> List[Note]:
        """Case-insensitive full-text search over title and body using ILIKE."""
        term = f"%{query}%"
        with self._db.connection.cursor() as cur:
            if case_number:
                cur.execute(
                    """
                    SELECT * FROM notes
                    WHERE case_number = %s
                      AND (title ILIKE %s OR body ILIKE %s)
                    ORDER BY created_at
                    """,
                    (case_number, term, term),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM notes
                    WHERE title ILIKE %s OR body ILIKE %s
                    ORDER BY created_at
                    """,
                    (term, term),
                )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_archived(self, case_number: str) -> List[Note]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM notes WHERE case_number = %s AND status = %s ORDER BY created_at",
                (case_number, NoteStatus.ARCHIVED.value),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_pending_approval(self, case_number: str) -> List[Note]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM notes WHERE case_number = %s AND status = %s ORDER BY created_at",
                (case_number, NoteStatus.PENDING_APPROVAL.value),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_tag(self, case_number: str, tag: str) -> List[Note]:
        """Return notes where the tags JSON array contains the given tag."""
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM notes WHERE case_number = %s ORDER BY created_at",
                (case_number,),
            )
            rows = cur.fetchall()
        tag_lower = tag.strip().lower()
        return [
            self._to_entity(r) for r in rows
            if any(t.lower() == tag_lower for t in self._parse_tags(r.get("tags")))
        ]

    def get_by_type(self, case_number: str, note_type: str) -> List[Note]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM notes WHERE case_number = %s AND note_type = %s ORDER BY created_at",
                (case_number, note_type),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_available_tags(self, case_number: str) -> List[str]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT tags FROM notes WHERE case_number = %s",
                (case_number,),
            )
            rows = cur.fetchall()
        tags: set = set()
        for r in rows:
            tags.update(self._parse_tags(r.get("tags")))
        return sorted(tags)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_dt(value) -> Optional[datetime]:
        """Accept datetime objects (psycopg2) or ISO strings (fallback)."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    @staticmethod
    def _parse_tags(raw) -> List[str]:
        if not raw:
            return []
        try:
            return json.loads(raw) if isinstance(raw, str) else list(raw)
        except (ValueError, TypeError):
            return []

    def _to_entity(self, row: dict) -> Note:
        return Note(
            id=row["id"],
            case_number=row["case_number"],
            title=row["title"],
            body=row["body"] or "",
            created_by=row["created_by"],
            created_at=self._parse_dt(row["created_at"]) or datetime.utcnow(),
            modified_at=self._parse_dt(row["modified_at"]),
            modified_by=row.get("modified_by"),
            status=NoteStatus(row["status"]) if row.get("status") else NoteStatus.ACTIVE,
            tags=self._parse_tags(row.get("tags")),
            note_type=row.get("note_type"),
            priority=row.get("priority"),
            approved_by=row.get("approved_by"),
            approved_at=self._parse_dt(row.get("approved_at")),
            approval_comments=row.get("approval_comments"),
        )

