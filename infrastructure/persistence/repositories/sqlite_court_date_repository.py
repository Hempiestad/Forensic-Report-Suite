"""SQLite-backed court date repository implementation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from application.interfaces.i_court_date_repository import ICourtDateRepository
from domain.entities.court_date import CourtDate
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteCourtDateRepository(ICourtDateRepository):
    """Concrete SQLite adapter for court date persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[CourtDate]:
        row = self._db.connection.execute(
            "SELECT * FROM court_dates WHERE id = ?", (int(entity_id),)
        ).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[CourtDate]:
        rows = self._db.connection.execute("SELECT * FROM court_dates ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: CourtDate) -> None:
        self._db.connection.execute(
            """
            INSERT INTO court_dates (
                id, case_number, date_type, court_date, location, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.id,
                entity.case_number,
                entity.date_type,
                self._dt_to_iso(entity.court_date),
                entity.location,
                entity.notes,
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
            ),
        )

    def update(self, entity: CourtDate) -> None:
        self._db.connection.execute(
            """
            UPDATE court_dates
            SET case_number = ?,
                date_type = ?,
                court_date = ?,
                location = ?,
                notes = ?,
                created_at = ?
            WHERE id = ?
            """,
            (
                entity.case_number,
                entity.date_type,
                self._dt_to_iso(entity.court_date),
                entity.location,
                entity.notes,
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM court_dates WHERE id = ?", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM court_dates WHERE id = ? LIMIT 1", (int(entity_id),)
        ).fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> List[CourtDate]:
        rows = self._db.connection.execute(
            "SELECT * FROM court_dates WHERE case_number = ? ORDER BY court_date",
            (case_number,),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_upcoming(self, days_ahead: int = 90) -> List[CourtDate]:
        """Get court dates within the next N days."""
        now = datetime.utcnow()
        future = now + timedelta(days=days_ahead)

        now_iso = now.isoformat()
        future_iso = future.isoformat()

        rows = self._db.connection.execute(
            """
            SELECT * FROM court_dates
            WHERE court_date >= ?
              AND court_date <= ?
            ORDER BY court_date ASC
            """,
            (now_iso, future_iso),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row) -> CourtDate:
        """Convert database row to CourtDate entity."""
        return CourtDate(
            id=int(row["id"]),
            case_number=row["case_number"],
            date_type=row["date_type"],
            court_date=self._iso_to_dt(row["court_date"]),
            location=row["location"],
            notes=row["notes"],
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
