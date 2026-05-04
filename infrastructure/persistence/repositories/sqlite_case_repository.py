"""SQLite-backed case repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_case_repository import ICaseRepository
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteCaseRepository(ICaseRepository):
    """Concrete SQLite adapter for case persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Case]:
        return self.get_by_case_number(entity_id)

    def get_all(self) -> List[Case]:
        rows = self._db.connection.execute("SELECT * FROM cases ORDER BY case_number").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Case) -> None:
        self._db.connection.execute(
            """
            INSERT INTO cases (
                case_number, title, assigned_to, created_by, status,
                examiner_id, review_comments, trial_date, sentencing_date,
                created_at, modified_at, modified_by, peer_reviewers
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_row_values(entity),
        )

    def update(self, entity: Case) -> None:
        self._db.connection.execute(
            """
            UPDATE cases
            SET title = ?,
                assigned_to = ?,
                created_by = ?,
                status = ?,
                examiner_id = ?,
                review_comments = ?,
                trial_date = ?,
                sentencing_date = ?,
                created_at = ?,
                modified_at = ?,
                modified_by = ?,
                peer_reviewers = ?
            WHERE case_number = ?
            """,
            (
                entity.title,
                entity.assigned_to,
                entity.created_by,
                entity.status.value,
                entity.examiner_id,
                entity.review_comments,
                self._dt_to_iso(entity.trial_date),
                self._dt_to_iso(entity.sentencing_date),
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                self._dt_to_iso(entity.modified_at) or datetime.utcnow().isoformat(),
                entity.modified_by,
                json.dumps(entity.peer_reviewers),
                entity.case_number,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM cases WHERE case_number = ?", (entity_id,))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM cases WHERE case_number = ? LIMIT 1", (entity_id,)
        ).fetchone()
        return row is not None

    def get_by_case_number(self, case_number: str) -> Optional[Case]:
        row = self._db.connection.execute(
            "SELECT * FROM cases WHERE case_number = ?", (case_number,)
        ).fetchone()
        return self._to_entity(row) if row else None

    def get_by_status(self, status: CaseStatus) -> List[Case]:
        rows = self._db.connection.execute(
            "SELECT * FROM cases WHERE status = ? ORDER BY case_number", (status.value,)
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_assigned_to(self, username: str) -> List[Case]:
        rows = self._db.connection.execute(
            "SELECT * FROM cases WHERE assigned_to = ? ORDER BY case_number", (username,)
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def search(self, query: str) -> List[Case]:
        term = f"%{query.lower()}%"
        rows = self._db.connection.execute(
            """
            SELECT * FROM cases
            WHERE lower(case_number) LIKE ?
               OR lower(title) LIKE ?
               OR lower(assigned_to) LIKE ?
            ORDER BY case_number
            """,
            (term, term, term),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row) -> Case:
        case = Case.create(
            case_number=row["case_number"],
            title=row["title"],
            assigned_to=row["assigned_to"],
            created_by=row["created_by"],
            examiner_id=row["examiner_id"],
        )
        case.status = self._parse_status(row["status"])
        case.review_comments = row["review_comments"]
        case.trial_date = self._iso_to_dt(row["trial_date"])
        case.sentencing_date = self._iso_to_dt(row["sentencing_date"])
        case.created_at = self._iso_to_dt(row["created_at"]) or case.created_at
        case.modified_at = self._iso_to_dt(row["modified_at"]) or case.modified_at
        case.modified_by = row["modified_by"]
        case.peer_reviewers = self._parse_reviewers(row["peer_reviewers"])
        return case

    def _to_row_values(self, entity: Case) -> tuple:
        return (
            entity.case_number,
            entity.title,
            entity.assigned_to,
            entity.created_by,
            entity.status.value,
            entity.examiner_id,
            entity.review_comments,
            self._dt_to_iso(entity.trial_date),
            self._dt_to_iso(entity.sentencing_date),
            self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
            self._dt_to_iso(entity.modified_at) or datetime.utcnow().isoformat(),
            entity.modified_by,
            json.dumps(entity.peer_reviewers),
        )

    @staticmethod
    def _parse_status(raw: str) -> CaseStatus:
        try:
            return CaseStatus(raw)
        except ValueError:
            return CaseStatus.DRAFT

    @staticmethod
    def _parse_reviewers(raw: Optional[str]) -> List[str]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                return [str(v) for v in value]
        except Exception:
            return []
        return []

    @staticmethod
    def _dt_to_iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @staticmethod
    def _iso_to_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
