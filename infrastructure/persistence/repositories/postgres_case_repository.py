"""PostgreSQL-backed case repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_case_repository import ICaseRepository
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLCaseRepository(ICaseRepository):
    """Concrete PostgreSQL adapter for case persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Case]:
        return self.get_by_case_number(entity_id)

    def get_all(self) -> List[Case]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM cases ORDER BY case_number")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Case) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cases (
                    case_number, title, assigned_to, created_by, status,
                    examiner_id, review_comments, trial_date, sentencing_date,
                    created_at, modified_at, modified_by, peer_reviewers
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                self._to_row_values(entity),
            )

    def update(self, entity: Case) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE cases
                SET title = %s,
                    assigned_to = %s,
                    created_by = %s,
                    status = %s,
                    examiner_id = %s,
                    review_comments = %s,
                    trial_date = %s,
                    sentencing_date = %s,
                    created_at = %s,
                    modified_at = %s,
                    modified_by = %s,
                    peer_reviewers = %s
                WHERE case_number = %s
                """,
                (
                    entity.title,
                    entity.assigned_to,
                    entity.created_by,
                    entity.status.value,
                    entity.examiner_id,
                    entity.review_comments,
                    entity.trial_date,
                    entity.sentencing_date,
                    entity.created_at,
                    entity.modified_at,
                    entity.modified_by,
                    json.dumps(entity.peer_reviewers),
                    entity.case_number,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM cases WHERE case_number = %s", (entity_id,))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM cases WHERE case_number = %s LIMIT 1", (entity_id,))
            row = cur.fetchone()
        return row is not None

    def get_by_case_number(self, case_number: str) -> Optional[Case]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM cases WHERE case_number = %s", (case_number,))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_by_status(self, status: CaseStatus) -> List[Case]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM cases WHERE status = %s ORDER BY case_number", (status.value,))
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_assigned_to(self, username: str) -> List[Case]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM cases WHERE assigned_to = %s ORDER BY case_number", (username,))
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def search(self, query: str) -> List[Case]:
        term = f"%{query.lower()}%"
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM cases
                WHERE lower(case_number) LIKE %s
                   OR lower(title) LIKE %s
                   OR lower(assigned_to) LIKE %s
                ORDER BY case_number
                """,
                (term, term, term),
            )
            rows = cur.fetchall()
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
        case.trial_date = row["trial_date"]
        case.sentencing_date = row["sentencing_date"]
        case.created_at = row["created_at"] or case.created_at
        case.modified_at = row["modified_at"] or case.modified_at
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
            entity.trial_date,
            entity.sentencing_date,
            entity.created_at or datetime.utcnow(),
            entity.modified_at or datetime.utcnow(),
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
    def _parse_reviewers(raw) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(v) for v in raw]
        if isinstance(raw, str):
            try:
                value = json.loads(raw)
                if isinstance(value, list):
                    return [str(v) for v in value]
            except Exception:
                return []
        return []
