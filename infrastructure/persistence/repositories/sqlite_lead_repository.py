"""infrastructure/persistence/repositories/sqlite_lead_repository.py — SQLite lead repository."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
from domain.entities.investigative_lead import InvestigativeLead
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteInvestigativeLeadRepository(IInvestigativeLeadRepository):
    """Concrete SQLite adapter for InvestigativeLead persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    # ------------------------------------------------------------------ #
    # IRepository                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, entity_id: str) -> Optional[InvestigativeLead]:
        row = self._db.connection.execute(
            "SELECT * FROM investigative_leads WHERE id = ?", (int(entity_id),)
        ).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[InvestigativeLead]:
        rows = self._db.connection.execute(
            "SELECT * FROM investigative_leads ORDER BY id"
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: InvestigativeLead) -> None:
        self._db.connection.execute(
            """
            INSERT INTO investigative_leads (
                id, case_number, name, source, description,
                completed, completed_at, completed_by,
                created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_row_values(entity),
        )

    def update(self, entity: InvestigativeLead) -> None:
        self._db.connection.execute(
            """
            UPDATE investigative_leads
            SET case_number = ?,
                name = ?,
                source = ?,
                description = ?,
                completed = ?,
                completed_at = ?,
                completed_by = ?,
                created_at = ?,
                modified_at = ?
            WHERE id = ?
            """,
            (
                entity.case_number,
                entity.name,
                entity.source,
                entity.description,
                1 if entity.completed else 0,
                self._dt(entity.completed_at),
                entity.completed_by,
                self._dt(entity.created_at),
                self._dt(entity.modified_at),
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute(
            "DELETE FROM investigative_leads WHERE id = ?", (int(entity_id),)
        )

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM investigative_leads WHERE id = ? LIMIT 1", (int(entity_id),)
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # IInvestigativeLeadRepository                                         #
    # ------------------------------------------------------------------ #

    def get_for_case(self, case_number: str) -> List[InvestigativeLead]:
        rows = self._db.connection.execute(
            "SELECT * FROM investigative_leads WHERE case_number = ? ORDER BY id",
            (case_number,),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_open_for_case(self, case_number: str) -> List[InvestigativeLead]:
        rows = self._db.connection.execute(
            "SELECT * FROM investigative_leads WHERE case_number = ? AND completed = 0 ORDER BY id",
            (case_number,),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

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

    def _to_row_values(self, entity: InvestigativeLead) -> tuple:
        return (
            entity.id,
            entity.case_number,
            entity.name,
            entity.source,
            entity.description,
            1 if entity.completed else 0,
            self._dt(entity.completed_at),
            entity.completed_by,
            self._dt(entity.created_at),
            self._dt(entity.modified_at),
        )

    def _to_entity(self, row) -> InvestigativeLead:
        return InvestigativeLead(
            id=int(row["id"]),
            case_number=row["case_number"],
            name=row["name"],
            source=row["source"],
            description=row["description"],
            completed=bool(row["completed"]),
            completed_at=self._parse_dt(row["completed_at"]),
            completed_by=row["completed_by"],
            created_at=self._parse_dt(row["created_at"]) or datetime.utcnow(),
            modified_at=self._parse_dt(row["modified_at"]) or datetime.utcnow(),
        )
