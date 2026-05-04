"""PostgreSQL-backed Evidence repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_evidence_repository import IEvidenceRepository
from domain.entities.evidence import Evidence
from domain.enums.evidence_status import EvidenceStatus
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLEvidenceRepository(IEvidenceRepository):
    """Concrete PostgreSQL adapter for Evidence persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    # ------------------------------------------------------------------ #
    # IRepository                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, entity_id: str) -> Optional[Evidence]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM evidence WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Evidence]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM evidence ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Evidence) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO evidence (
                    id, case_number, evidence_item_number, item_type,
                    physical_description, digital_make, digital_model, digital_type,
                    digital_serial_number, digital_storage_size, password,
                    status, imaged_date, analyzed_date, completed_date,
                    evidence_found, created_at, modified_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    entity.id,
                    entity.case_number,
                    entity.evidence_item_number,
                    entity.item_type,
                    entity.physical_description,
                    entity.digital_make,
                    entity.digital_model,
                    entity.digital_type,
                    entity.digital_serial_number,
                    entity.digital_storage_size,
                    entity.password,
                    entity.status.value,
                    entity.imaged_date,
                    entity.analyzed_date,
                    entity.completed_date,
                    entity.evidence_found,
                    entity.created_at or datetime.utcnow(),
                    entity.modified_at or datetime.utcnow(),
                ),
            )

    def update(self, entity: Evidence) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE evidence
                SET case_number = %s,
                    evidence_item_number = %s,
                    item_type = %s,
                    physical_description = %s,
                    digital_make = %s,
                    digital_model = %s,
                    digital_type = %s,
                    digital_serial_number = %s,
                    digital_storage_size = %s,
                    password = %s,
                    status = %s,
                    imaged_date = %s,
                    analyzed_date = %s,
                    completed_date = %s,
                    evidence_found = %s,
                    created_at = %s,
                    modified_at = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.evidence_item_number,
                    entity.item_type,
                    entity.physical_description,
                    entity.digital_make,
                    entity.digital_model,
                    entity.digital_type,
                    entity.digital_serial_number,
                    entity.digital_storage_size,
                    entity.password,
                    entity.status.value,
                    entity.imaged_date,
                    entity.analyzed_date,
                    entity.completed_date,
                    entity.evidence_found,
                    entity.created_at or datetime.utcnow(),
                    entity.modified_at or datetime.utcnow(),
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM evidence WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM evidence WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # IEvidenceRepository                                                  #
    # ------------------------------------------------------------------ #

    def get_for_case(self, case_number: str) -> List[Evidence]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM evidence WHERE case_number = %s ORDER BY id",
                (case_number,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_item_number(self, case_number: str, item_number: str) -> Optional[Evidence]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM evidence
                WHERE case_number = %s AND evidence_item_number = %s
                LIMIT 1
                """,
                (case_number, item_number),
            )
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_by_status(self, status: EvidenceStatus) -> List[Evidence]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM evidence WHERE status = %s ORDER BY id",
                (status.value,),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

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

    def _to_entity(self, row: dict) -> Evidence:
        return Evidence(
            id=int(row["id"]),
            case_number=row["case_number"],
            evidence_item_number=row["evidence_item_number"],
            item_type=row["item_type"],
            physical_description=row["physical_description"],
            digital_make=row["digital_make"],
            digital_model=row["digital_model"],
            digital_type=row["digital_type"],
            digital_serial_number=row["digital_serial_number"],
            digital_storage_size=row["digital_storage_size"],
            password=row["password"],
            status=EvidenceStatus(row["status"]),
            imaged_date=self._parse_dt(row["imaged_date"]),
            analyzed_date=self._parse_dt(row["analyzed_date"]),
            completed_date=self._parse_dt(row["completed_date"]),
            evidence_found=row["evidence_found"],
            created_at=self._parse_dt(row["created_at"]) or datetime.utcnow(),
            modified_at=self._parse_dt(row["modified_at"]) or datetime.utcnow(),
        )
