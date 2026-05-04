"""PostgreSQL-backed legal process repository implementation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from application.interfaces.i_legal_process_repository import ILegalProcessRepository
from domain.entities.legal_process import LegalProcess
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLLegalProcessRepository(ILegalProcessRepository):
    """Concrete PostgreSQL adapter for legal process persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[LegalProcess]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM legal_processes WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[LegalProcess]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM legal_processes ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: LegalProcess) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO legal_processes (
                    id, case_number, process_type, provider, status,
                    submission_date, due_date, expiration_date, received_date,
                    analysis_start_date, completed_date,
                    investigator_approved, investigator_approved_by, investigator_approved_at,
                    state_attorney_approved, state_attorney_approved_by, state_attorney_approved_at,
                    judicial_approved, judicial_approved_by, judicial_approved_at,
                    notes, ndr, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entity.id,
                    entity.case_number,
                    entity.process_type,
                    entity.provider,
                    entity.status,
                    entity.submission_date,
                    entity.due_date,
                    entity.expiration_date,
                    entity.received_date,
                    entity.analysis_start_date,
                    entity.completed_date,
                    entity.investigator_approved,
                    entity.investigator_approved_by,
                    entity.investigator_approved_at,
                    entity.state_attorney_approved,
                    entity.state_attorney_approved_by,
                    entity.state_attorney_approved_at,
                    entity.judicial_approved,
                    entity.judicial_approved_by,
                    entity.judicial_approved_at,
                    entity.notes,
                    entity.ndr,
                    entity.created_at or datetime.utcnow(),
                ),
            )

    def update(self, entity: LegalProcess) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE legal_processes
                SET case_number = %s,
                    process_type = %s,
                    provider = %s,
                    status = %s,
                    submission_date = %s,
                    due_date = %s,
                    expiration_date = %s,
                    received_date = %s,
                    analysis_start_date = %s,
                    completed_date = %s,
                    investigator_approved = %s,
                    investigator_approved_by = %s,
                    investigator_approved_at = %s,
                    state_attorney_approved = %s,
                    state_attorney_approved_by = %s,
                    state_attorney_approved_at = %s,
                    judicial_approved = %s,
                    judicial_approved_by = %s,
                    judicial_approved_at = %s,
                    notes = %s,
                    ndr = %s,
                    created_at = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.process_type,
                    entity.provider,
                    entity.status,
                    entity.submission_date,
                    entity.due_date,
                    entity.expiration_date,
                    entity.received_date,
                    entity.analysis_start_date,
                    entity.completed_date,
                    entity.investigator_approved,
                    entity.investigator_approved_by,
                    entity.investigator_approved_at,
                    entity.state_attorney_approved,
                    entity.state_attorney_approved_by,
                    entity.state_attorney_approved_at,
                    entity.judicial_approved,
                    entity.judicial_approved_by,
                    entity.judicial_approved_at,
                    entity.notes,
                    entity.ndr,
                    entity.created_at or datetime.utcnow(),
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM legal_processes WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM legal_processes WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> List[LegalProcess]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM legal_processes WHERE case_number = %s ORDER BY id",
                (case_number,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_overdue(self) -> List[LegalProcess]:
        """Return processes currently overdue (due_date is past and not completed)."""
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM legal_processes
                WHERE due_date IS NOT NULL
                  AND due_date < %s
                  AND status != 'completed'
                ORDER BY due_date ASC
                """,
                (datetime.utcnow(),),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_due_soon(self, days: int = 7) -> List[LegalProcess]:
        """Return processes due within specified days."""
        now = datetime.utcnow()
        future = now + timedelta(days=days)

        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM legal_processes
                WHERE due_date IS NOT NULL
                  AND due_date >= %s
                  AND due_date <= %s
                  AND status != 'completed'
                ORDER BY due_date ASC
                """,
                (now, future),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row: dict) -> LegalProcess:
        """Convert database row to LegalProcess entity."""
        return LegalProcess(
            id=int(row["id"]),
            case_number=row["case_number"],
            process_type=row["process_type"],
            provider=row["provider"],
            status=row["status"],
            submission_date=row["submission_date"],
            due_date=row["due_date"],
            expiration_date=row["expiration_date"],
            received_date=row["received_date"],
            analysis_start_date=row["analysis_start_date"],
            completed_date=row["completed_date"],
            investigator_approved=row["investigator_approved"],
            investigator_approved_by=row["investigator_approved_by"],
            investigator_approved_at=row["investigator_approved_at"],
            state_attorney_approved=row["state_attorney_approved"],
            state_attorney_approved_by=row["state_attorney_approved_by"],
            state_attorney_approved_at=row["state_attorney_approved_at"],
            judicial_approved=row["judicial_approved"],
            judicial_approved_by=row["judicial_approved_by"],
            judicial_approved_at=row["judicial_approved_at"],
            notes=row["notes"],
            ndr=row["ndr"],
            created_at=row["created_at"] or datetime.utcnow(),
        )
