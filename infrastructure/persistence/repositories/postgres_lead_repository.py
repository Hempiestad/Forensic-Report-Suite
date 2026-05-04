"""infrastructure/persistence/repositories/postgres_lead_repository.py — PostgreSQL lead repository."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
from domain.entities.investigative_lead import InvestigativeLead
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLInvestigativeLeadRepository(IInvestigativeLeadRepository):
    """Concrete PostgreSQL adapter for InvestigativeLead persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    # ------------------------------------------------------------------ #
    # IRepository                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, entity_id: str) -> Optional[InvestigativeLead]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM investigative_leads WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[InvestigativeLead]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM investigative_leads ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: InvestigativeLead) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO investigative_leads (
                    id, case_number, name, source, description,
                    completed, completed_at, completed_by,
                    created_at, modified_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entity.id,
                    entity.case_number,
                    entity.name,
                    entity.source,
                    entity.description,
                    entity.completed,
                    entity.completed_at,
                    entity.completed_by,
                    entity.created_at or datetime.utcnow(),
                    entity.modified_at or datetime.utcnow(),
                ),
            )

    def update(self, entity: InvestigativeLead) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE investigative_leads
                SET case_number = %s,
                    name = %s,
                    source = %s,
                    description = %s,
                    completed = %s,
                    completed_at = %s,
                    completed_by = %s,
                    created_at = %s,
                    modified_at = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.name,
                    entity.source,
                    entity.description,
                    entity.completed,
                    entity.completed_at,
                    entity.completed_by,
                    entity.created_at or datetime.utcnow(),
                    entity.modified_at or datetime.utcnow(),
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "DELETE FROM investigative_leads WHERE id = %s", (int(entity_id),)
            )

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM investigative_leads WHERE id = %s LIMIT 1", (int(entity_id),)
            )
            row = cur.fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # IInvestigativeLeadRepository                                         #
    # ------------------------------------------------------------------ #

    def get_for_case(self, case_number: str) -> List[InvestigativeLead]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM investigative_leads WHERE case_number = %s ORDER BY id",
                (case_number,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_open_for_case(self, case_number: str) -> List[InvestigativeLead]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM investigative_leads
                WHERE case_number = %s AND completed = FALSE
                ORDER BY id
                """,
                (case_number,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_dt(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _to_entity(self, row: dict) -> InvestigativeLead:
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
