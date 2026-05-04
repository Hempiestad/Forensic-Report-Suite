"""PostgreSQL-backed court date repository implementation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from application.interfaces.i_court_date_repository import ICourtDateRepository
from domain.entities.court_date import CourtDate
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLCourtDateRepository(ICourtDateRepository):
    """Concrete PostgreSQL adapter for court date persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[CourtDate]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM court_dates WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[CourtDate]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM court_dates ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: CourtDate) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO court_dates (
                    id, case_number, date_type, court_date, location, notes, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entity.id,
                    entity.case_number,
                    entity.date_type,
                    entity.court_date,
                    entity.location,
                    entity.notes,
                    entity.created_at or datetime.utcnow(),
                ),
            )

    def update(self, entity: CourtDate) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE court_dates
                SET case_number = %s,
                    date_type = %s,
                    court_date = %s,
                    location = %s,
                    notes = %s,
                    created_at = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.date_type,
                    entity.court_date,
                    entity.location,
                    entity.notes,
                    entity.created_at or datetime.utcnow(),
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM court_dates WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM court_dates WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> List[CourtDate]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM court_dates WHERE case_number = %s ORDER BY court_date",
                (case_number,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_upcoming(self, days_ahead: int = 90) -> List[CourtDate]:
        """Get court dates within the next N days."""
        now = datetime.utcnow()
        future = now + timedelta(days=days_ahead)

        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM court_dates
                WHERE court_date >= %s
                  AND court_date <= %s
                ORDER BY court_date ASC
                """,
                (now, future),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row: dict) -> CourtDate:
        """Convert database row to CourtDate entity."""
        return CourtDate(
            id=int(row["id"]),
            case_number=row["case_number"],
            date_type=row["date_type"],
            court_date=row["court_date"],
            location=row["location"],
            notes=row["notes"],
            created_at=row["created_at"] or datetime.utcnow(),
        )
