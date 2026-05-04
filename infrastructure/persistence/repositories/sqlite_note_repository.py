"""infrastructure/persistence/repositories/sqlite_note_repository.py — SQLite Note repository."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_note_repository import INoteRepository
from domain.entities.note import Note
from domain.enums.note_status import NoteStatus
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteNoteRepository(INoteRepository):
    """Concrete SQLite adapter for Note persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    # ------------------------------------------------------------------ #
    # IRepository                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, entity_id: str) -> Optional[Note]:
        row = self._db.connection.execute(
            "SELECT * FROM notes WHERE id = ?", (entity_id,)
        ).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Note]:
        rows = self._db.connection.execute("SELECT * FROM notes ORDER BY created_at").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Note) -> None:
        self._db.connection.execute(
            """
            INSERT INTO notes (id, case_number, title, body, created_by, created_at,
                               modified_at, modified_by, status, tags, note_type,
                               priority, approved_by, approved_at, approval_comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_row_values(entity),
        )

    def update(self, entity: Note) -> None:
        self._db.connection.execute(
            """
            UPDATE notes
            SET case_number        = ?,
                title              = ?,
                body               = ?,
                created_by         = ?,
                created_at         = ?,
                modified_at        = ?,
                modified_by        = ?,
                status             = ?,
                tags               = ?,
                note_type          = ?,
                priority           = ?,
                approved_by        = ?,
                approved_at        = ?,
                approval_comments  = ?
            WHERE id = ?
            """,
            (
                entity.case_number,
                entity.title,
                entity.body,
                entity.created_by,
                self._dt(entity.created_at),
                self._dt(entity.modified_at),
                entity.modified_by,
                entity.status.value if entity.status else NoteStatus.ACTIVE.value,
                json.dumps(entity.tags),
                entity.note_type,
                entity.priority,
                entity.approved_by,
                self._dt(entity.approved_at),
                entity.approval_comments,
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM notes WHERE id = ?", (entity_id,))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM notes WHERE id = ? LIMIT 1", (entity_id,)
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # INoteRepository                                                      #
    # ------------------------------------------------------------------ #

    def get_for_case(self, case_number: str) -> List[Note]:
        rows = self._db.connection.execute(
            "SELECT * FROM notes WHERE case_number = ? AND status = ? ORDER BY created_at",
            (case_number, NoteStatus.ACTIVE.value),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def search(self, query: str, case_number: Optional[str] = None) -> List[Note]:
        term = f"%{query.lower()}%"
        if case_number:
            rows = self._db.connection.execute(
                """
                SELECT * FROM notes
                WHERE case_number = ?
                  AND (lower(title) LIKE ? OR lower(body) LIKE ?)
                ORDER BY created_at
                """,
                (case_number, term, term),
            ).fetchall()
        else:
            rows = self._db.connection.execute(
                """
                SELECT * FROM notes
                WHERE lower(title) LIKE ? OR lower(body) LIKE ?
                ORDER BY created_at
                """,
                (term, term),
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_archived(self, case_number: str) -> List[Note]:
        rows = self._db.connection.execute(
            "SELECT * FROM notes WHERE case_number = ? AND status = ? ORDER BY created_at",
            (case_number, NoteStatus.ARCHIVED.value),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_pending_approval(self, case_number: str) -> List[Note]:
        rows = self._db.connection.execute(
            "SELECT * FROM notes WHERE case_number = ? AND status = ? ORDER BY created_at",
            (case_number, NoteStatus.PENDING_APPROVAL.value),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_tag(self, case_number: str, tag: str) -> List[Note]:
        """Return notes that carry the given tag (JSON array stored in column)."""
        rows = self._db.connection.execute(
            "SELECT * FROM notes WHERE case_number = ? ORDER BY created_at",
            (case_number,),
        ).fetchall()
        tag_lower = tag.strip().lower()
        return [
            self._to_entity(r) for r in rows
            if any(t.lower() == tag_lower for t in self._parse_tags(r["tags"]))
        ]

    def get_by_type(self, case_number: str, note_type: str) -> List[Note]:
        rows = self._db.connection.execute(
            "SELECT * FROM notes WHERE case_number = ? AND note_type = ? ORDER BY created_at",
            (case_number, note_type),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_available_tags(self, case_number: str) -> List[str]:
        rows = self._db.connection.execute(
            "SELECT tags FROM notes WHERE case_number = ?",
            (case_number,),
        ).fetchall()
        tags: set = set()
        for r in rows:
            tags.update(self._parse_tags(r["tags"]))
        return sorted(tags)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _dt(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
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

    def _to_row_values(self, entity: Note) -> tuple:
        keys = list(dict(entity.__dict__).keys()) if False else None  # noqa
        return (
            entity.id,
            entity.case_number,
            entity.title,
            entity.body,
            entity.created_by,
            self._dt(entity.created_at),
            self._dt(entity.modified_at),
            entity.modified_by,
            entity.status.value if entity.status else NoteStatus.ACTIVE.value,
            json.dumps(entity.tags),
            entity.note_type,
            entity.priority,
            entity.approved_by,
            self._dt(entity.approved_at),
            entity.approval_comments,
        )

    def _to_entity(self, row) -> Note:
        keys = row.keys() if hasattr(row, "keys") else []
        return Note(
            id=row["id"],
            case_number=row["case_number"],
            title=row["title"],
            body=row["body"] or "",
            created_by=row["created_by"],
            created_at=self._parse_dt(row["created_at"]) or datetime.utcnow(),
            modified_at=self._parse_dt(row["modified_at"]),
            modified_by=row["modified_by"],
            status=NoteStatus(row["status"]) if "status" in keys and row["status"] else NoteStatus.ACTIVE,
            tags=self._parse_tags(row["tags"] if "tags" in keys else None),
            note_type=row["note_type"] if "note_type" in keys else None,
            priority=row["priority"] if "priority" in keys else None,
            approved_by=row["approved_by"] if "approved_by" in keys else None,
            approved_at=self._parse_dt(row["approved_at"]) if "approved_at" in keys else None,
            approval_comments=row["approval_comments"] if "approval_comments" in keys else None,
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _dt(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
