"""SQLite-backed report repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_report_repository import IReportRepository
from domain.entities.report import Report
from domain.enums.report_status import ReportStatus
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteReportRepository(IReportRepository):
    """Concrete SQLite adapter for report persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Report]:
        row = self._db.connection.execute("SELECT * FROM reports WHERE id = ?", (int(entity_id),)).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Report]:
        rows = self._db.connection.execute("SELECT * FROM reports ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Report) -> None:
        self._db.connection.execute(
            """
            INSERT INTO reports (
                id, case_number, report_html, report_html_encrypted, status, appendices,
                final_pdf_hash, finalized_by, finalized_at, created_at, created_by, modified_at, modified_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.id,
                entity.case_number,
                entity.report_html,
                entity.report_html_encrypted,
                entity.status.value,
                json.dumps(entity.appendices),
                entity.final_pdf_hash,
                entity.finalized_by,
                self._dt_to_iso(entity.finalized_at),
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                entity.created_by,
                self._dt_to_iso(entity.modified_at) or datetime.utcnow().isoformat(),
                entity.modified_by,
            ),
        )

    def update(self, entity: Report) -> None:
        self._db.connection.execute(
            """
            UPDATE reports
            SET case_number = ?,
                report_html = ?,
                report_html_encrypted = ?,
                status = ?,
                appendices = ?,
                final_pdf_hash = ?,
                finalized_by = ?,
                finalized_at = ?,
                created_at = ?,
                created_by = ?,
                modified_at = ?,
                modified_by = ?
            WHERE id = ?
            """,
            (
                entity.case_number,
                entity.report_html,
                entity.report_html_encrypted,
                entity.status.value,
                json.dumps(entity.appendices),
                entity.final_pdf_hash,
                entity.finalized_by,
                self._dt_to_iso(entity.finalized_at),
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                entity.created_by,
                self._dt_to_iso(entity.modified_at) or datetime.utcnow().isoformat(),
                entity.modified_by,
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM reports WHERE id = ?", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute("SELECT 1 FROM reports WHERE id = ? LIMIT 1", (int(entity_id),)).fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> Optional[Report]:
        row = self._db.connection.execute("SELECT * FROM reports WHERE case_number = ? LIMIT 1", (case_number,)).fetchone()
        return self._to_entity(row) if row else None

    def get_finalized(self, report_id: str) -> Optional[Report]:
        row = self._db.connection.execute(
            "SELECT * FROM reports WHERE id = ? AND status = ?",
            (int(report_id), ReportStatus.FINALIZED.value),
        ).fetchone()
        return self._to_entity(row) if row else None

    def _to_entity(self, row) -> Report:
        report = Report.create(
            id=int(row["id"]),
            case_number=row["case_number"],
            created_by=row["created_by"] or "",
        )
        report.report_html = row["report_html"]
        report.report_html_encrypted = row["report_html_encrypted"]
        report.status = self._parse_status(row["status"])
        report.final_pdf_hash = row["final_pdf_hash"]
        report.finalized_by = row["finalized_by"]
        report.finalized_at = self._iso_to_dt(row["finalized_at"])
        report.created_at = self._iso_to_dt(row["created_at"]) or report.created_at
        report.modified_at = self._iso_to_dt(row["modified_at"]) or report.modified_at
        report.modified_by = row["modified_by"]

        appendices = row["appendices"]
        if appendices:
            try:
                values = json.loads(appendices)
                if isinstance(values, list):
                    report._appendices.extend(str(v) for v in values)
            except Exception:
                pass
        return report

    @staticmethod
    def _parse_status(raw: str) -> ReportStatus:
        try:
            return ReportStatus(raw)
        except ValueError:
            return ReportStatus.DRAFT

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
