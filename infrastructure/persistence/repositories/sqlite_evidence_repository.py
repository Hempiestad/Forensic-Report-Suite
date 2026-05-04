"""infrastructure/persistence/repositories/sqlite_evidence_repository.py — SQLite Evidence repository."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_evidence_repository import IEvidenceRepository
from domain.entities.evidence import Evidence
from domain.enums.evidence_status import EvidenceStatus
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteEvidenceRepository(IEvidenceRepository):
    """Concrete SQLite adapter for Evidence persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    # ------------------------------------------------------------------ #
    # IRepository                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, entity_id: str) -> Optional[Evidence]:
        row = self._db.connection.execute(
            "SELECT * FROM evidence WHERE id = ?", (int(entity_id),)
        ).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Evidence]:
        rows = self._db.connection.execute("SELECT * FROM evidence ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Evidence) -> None:
        self._db.connection.execute(
            """
            INSERT INTO evidence (
                id, case_number, evidence_item_number, item_type,
                physical_description, digital_make, digital_model, digital_type,
                digital_serial_number, digital_storage_size, password,
                status, imaged_date, analyzed_date, completed_date,
                evidence_found, created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_row_values(entity),
        )

    def update(self, entity: Evidence) -> None:
        self._db.connection.execute(
            """
            UPDATE evidence
            SET case_number = ?,
                evidence_item_number = ?,
                item_type = ?,
                physical_description = ?,
                digital_make = ?,
                digital_model = ?,
                digital_type = ?,
                digital_serial_number = ?,
                digital_storage_size = ?,
                password = ?,
                status = ?,
                imaged_date = ?,
                analyzed_date = ?,
                completed_date = ?,
                evidence_found = ?,
                created_at = ?,
                modified_at = ?
            WHERE id = ?
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
                self._dt(entity.imaged_date),
                self._dt(entity.analyzed_date),
                self._dt(entity.completed_date),
                entity.evidence_found,
                self._dt(entity.created_at),
                self._dt(entity.modified_at),
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM evidence WHERE id = ?", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM evidence WHERE id = ? LIMIT 1", (int(entity_id),)
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # IEvidenceRepository                                                  #
    # ------------------------------------------------------------------ #

    def get_for_case(self, case_number: str) -> List[Evidence]:
        rows = self._db.connection.execute(
            "SELECT * FROM evidence WHERE case_number = ? ORDER BY id", (case_number,)
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_item_number(self, case_number: str, item_number: str) -> Optional[Evidence]:
        row = self._db.connection.execute(
            "SELECT * FROM evidence WHERE case_number = ? AND evidence_item_number = ? LIMIT 1",
            (case_number, item_number),
        ).fetchone()
        return self._to_entity(row) if row else None

    def get_by_status(self, status: EvidenceStatus) -> List[Evidence]:
        rows = self._db.connection.execute(
            "SELECT * FROM evidence WHERE status = ? ORDER BY id", (status.value,)
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

    def _to_row_values(self, entity: Evidence) -> tuple:
        return (
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
            self._dt(entity.imaged_date),
            self._dt(entity.analyzed_date),
            self._dt(entity.completed_date),
            entity.evidence_found,
            self._dt(entity.created_at),
            self._dt(entity.modified_at),
        )

    def _to_entity(self, row) -> Evidence:
        ev = Evidence(
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
        return ev
