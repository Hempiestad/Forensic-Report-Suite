"""SQLite-backed legal process repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_legal_process_repository import ILegalProcessRepository
from domain.entities.legal_process import LegalProcess
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteLegalProcessRepository(ILegalProcessRepository):
    """Concrete SQLite adapter for legal process persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[LegalProcess]:
        row = self._db.connection.execute("SELECT * FROM legal_processes WHERE id = ?", (int(entity_id),)).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[LegalProcess]:
        rows = self._db.connection.execute("SELECT * FROM legal_processes ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: LegalProcess) -> None:
        self._db.connection.execute(
            """
            INSERT INTO legal_processes (
                id, case_number, process_type, provider, status,
                submission_date, due_date, expiration_date, received_date,
                analysis_start_date, completed_date,
                investigator_approved, investigator_approved_by, investigator_approved_at,
                state_attorney_approved, state_attorney_approved_by, state_attorney_approved_at,
                judicial_approved, judicial_approved_by, judicial_approved_at,
                notes, ndr, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.id,
                entity.case_number,
                entity.process_type,
                entity.provider,
                entity.status,
                self._dt_to_iso(entity.submission_date),
                self._dt_to_iso(entity.due_date),
                self._dt_to_iso(entity.expiration_date),
                self._dt_to_iso(entity.received_date),
                self._dt_to_iso(entity.analysis_start_date),
                self._dt_to_iso(entity.completed_date),
                int(entity.investigator_approved),
                entity.investigator_approved_by,
                self._dt_to_iso(entity.investigator_approved_at),
                int(entity.state_attorney_approved),
                entity.state_attorney_approved_by,
                self._dt_to_iso(entity.state_attorney_approved_at),
                int(entity.judicial_approved),
                entity.judicial_approved_by,
                self._dt_to_iso(entity.judicial_approved_at),
                entity.notes,
                int(entity.ndr),
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
            ),
        )

    def update(self, entity: LegalProcess) -> None:
        self._db.connection.execute(
            """
            UPDATE legal_processes
            SET case_number = ?,
                process_type = ?,
                provider = ?,
                status = ?,
                submission_date = ?,
                due_date = ?,
                expiration_date = ?,
                received_date = ?,
                analysis_start_date = ?,
                completed_date = ?,
                investigator_approved = ?,
                investigator_approved_by = ?,
                investigator_approved_at = ?,
                state_attorney_approved = ?,
                state_attorney_approved_by = ?,
                state_attorney_approved_at = ?,
                judicial_approved = ?,
                judicial_approved_by = ?,
                judicial_approved_at = ?,
                notes = ?,
                ndr = ?,
                created_at = ?
            WHERE id = ?
            """,
            (
                entity.case_number,
                entity.process_type,
                entity.provider,
                entity.status,
                self._dt_to_iso(entity.submission_date),
                self._dt_to_iso(entity.due_date),
                self._dt_to_iso(entity.expiration_date),
                self._dt_to_iso(entity.received_date),
                self._dt_to_iso(entity.analysis_start_date),
                self._dt_to_iso(entity.completed_date),
                int(entity.investigator_approved),
                entity.investigator_approved_by,
                self._dt_to_iso(entity.investigator_approved_at),
                int(entity.state_attorney_approved),
                entity.state_attorney_approved_by,
                self._dt_to_iso(entity.state_attorney_approved_at),
                int(entity.judicial_approved),
                entity.judicial_approved_by,
                self._dt_to_iso(entity.judicial_approved_at),
                entity.notes,
                int(entity.ndr),
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM legal_processes WHERE id = ?", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM legal_processes WHERE id = ? LIMIT 1", (int(entity_id),)
        ).fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> List[LegalProcess]:
        rows = self._db.connection.execute(
            "SELECT * FROM legal_processes WHERE case_number = ? ORDER BY id",
            (case_number,),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_overdue(self) -> List[LegalProcess]:
        """Return processes currently overdue (due_date is past and not completed)."""
        now = datetime.utcnow().isoformat()
        rows = self._db.connection.execute(
            """
            SELECT * FROM legal_processes
            WHERE due_date IS NOT NULL
              AND due_date < ?
              AND status != 'completed'
            ORDER BY due_date ASC
            """,
            (now,),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_due_soon(self, days: int = 7) -> List[LegalProcess]:
        """Return processes due within specified days."""
        now = datetime.utcnow()
        future = now.replace(hour=23, minute=59, second=59)
        from datetime import timedelta
        future = now + timedelta(days=days)

        now_iso = now.isoformat()
        future_iso = future.isoformat()

        rows = self._db.connection.execute(
            """
            SELECT * FROM legal_processes
            WHERE due_date IS NOT NULL
              AND due_date >= ?
              AND due_date <= ?
              AND status != 'completed'
            ORDER BY due_date ASC
            """,
            (now_iso, future_iso),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row) -> LegalProcess:
        """Convert database row to LegalProcess entity."""
        return LegalProcess(
            id=int(row["id"]),
            case_number=row["case_number"],
            process_type=row["process_type"],
            provider=row["provider"],
            status=row["status"],
            submission_date=self._iso_to_dt(row["submission_date"]),
            due_date=self._iso_to_dt(row["due_date"]),
            expiration_date=self._iso_to_dt(row["expiration_date"]),
            received_date=self._iso_to_dt(row["received_date"]),
            analysis_start_date=self._iso_to_dt(row["analysis_start_date"]),
            completed_date=self._iso_to_dt(row["completed_date"]),
            investigator_approved=bool(row["investigator_approved"]),
            investigator_approved_by=row["investigator_approved_by"],
            investigator_approved_at=self._iso_to_dt(row["investigator_approved_at"]),
            state_attorney_approved=bool(row["state_attorney_approved"]),
            state_attorney_approved_by=row["state_attorney_approved_by"],
            state_attorney_approved_at=self._iso_to_dt(row["state_attorney_approved_at"]),
            judicial_approved=bool(row["judicial_approved"]),
            judicial_approved_by=row["judicial_approved_by"],
            judicial_approved_at=self._iso_to_dt(row["judicial_approved_at"]),
            notes=row["notes"],
            ndr=bool(row["ndr"]),
            created_at=self._iso_to_dt(row["created_at"]) or datetime.utcnow(),
        )

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
