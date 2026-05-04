"""PostgreSQL-backed report repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_report_repository import IReportRepository
from domain.entities.report import Report
from domain.enums.report_status import ReportStatus
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLReportRepository(IReportRepository):
    """Concrete PostgreSQL adapter for report persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Report]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM reports WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Report]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM reports ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Report) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reports (
                    id, case_number, report_html, report_html_encrypted, status, appendices,
                    final_pdf_hash, finalized_by, finalized_at, created_at, created_by, modified_at, modified_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                self._to_row_values(entity),
            )

    def update(self, entity: Report) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE reports
                SET case_number = %s,
                    report_html = %s,
                    report_html_encrypted = %s,
                    status = %s,
                    appendices = %s,
                    final_pdf_hash = %s,
                    finalized_by = %s,
                    finalized_at = %s,
                    created_at = %s,
                    created_by = %s,
                    modified_at = %s,
                    modified_by = %s
                WHERE id = %s
                """,
                (
                    entity.case_number,
                    entity.report_html,
                    entity.report_html_encrypted,
                    entity.status.value,
                    json.dumps(entity.appendices),
                    entity.final_pdf_hash,
                    entity.finalized_by,
                    entity.finalized_at,
                    entity.created_at,
                    entity.created_by,
                    entity.modified_at,
                    entity.modified_by,
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM reports WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM reports WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    def get_for_case(self, case_number: str) -> Optional[Report]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM reports WHERE case_number = %s LIMIT 1", (case_number,))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_finalized(self, report_id: str) -> Optional[Report]:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM reports WHERE id = %s AND status = %s",
                (int(report_id), ReportStatus.FINALIZED.value),
            )
            row = cur.fetchone()
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
        report.finalized_at = row["finalized_at"]
        report.created_at = row["created_at"] or datetime.utcnow()
        report.modified_at = row["modified_at"] or report.created_at
        report.modified_by = row["modified_by"]

        appendices = row["appendices"]
        if isinstance(appendices, list):
            for p in appendices:
                if p:
                    report._appendices.append(str(p))
        elif isinstance(appendices, str):
            try:
                decoded = json.loads(appendices)
                if isinstance(decoded, list):
                    for p in decoded:
                        if p:
                            report._appendices.append(str(p))
            except Exception:
                pass
        return report

    def _to_row_values(self, entity: Report) -> tuple:
        return (
            entity.id,
            entity.case_number,
            entity.report_html,
            entity.report_html_encrypted,
            entity.status.value,
            json.dumps(entity.appendices),
            entity.final_pdf_hash,
            entity.finalized_by,
            entity.finalized_at,
            entity.created_at or datetime.utcnow(),
            entity.created_by,
            entity.modified_at or datetime.utcnow(),
            entity.modified_by,
        )

    @staticmethod
    def _parse_status(raw: str) -> ReportStatus:
        try:
            return ReportStatus(raw)
        except ValueError:
            return ReportStatus.DRAFT
