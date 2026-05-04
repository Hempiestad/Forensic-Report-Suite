"""tests/integration/test_postgres_report_mapping.py

PostgreSQL Report repository: mapping tests (no live DB required) and
UnitOfWork provider selection. Live CRUD tests gated by FORENSIC_PG_DSN.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from domain.entities.report import Report
from domain.enums.report_status import ReportStatus
from infrastructure.persistence.repositories.postgres_report_repository import (
    PostgreSQLReportRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


_skip_pg = pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")


def _row(**overrides) -> dict:
    base: dict = {
        "id": 1,
        "case_number": "RPT-001",
        "report_html": "<p>Report body</p>",
        "report_html_encrypted": None,
        "status": "draft",
        "appendices": "[]",
        "final_pdf_hash": None,
        "finalized_by": None,
        "finalized_at": None,
        "created_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        "created_by": "alice",
        "modified_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        "modified_by": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _to_entity mapping (no live DB)
# ---------------------------------------------------------------------------

class TestPostgresReportMapping:
    def _repo(self) -> PostgreSQLReportRepository:
        return PostgreSQLReportRepository.__new__(PostgreSQLReportRepository)

    def test_basic_fields(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row())
        assert isinstance(r, Report)
        assert r.id == 1
        assert r.case_number == "RPT-001"
        assert r.created_by == "alice"
        assert r.report_html == "<p>Report body</p>"

    def test_status_draft(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(status="draft"))
        assert r.status == ReportStatus.DRAFT

    def test_status_finalized(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(status="finalized"))
        assert r.status == ReportStatus.FINALIZED

    def test_all_statuses(self) -> None:
        repo = self._repo()
        for status in ReportStatus:
            r = repo._to_entity(_row(status=status.value))
            assert r.status == status

    def test_unknown_status_falls_back_to_draft(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(status="garbage_value"))
        assert r.status == ReportStatus.DRAFT

    def test_appendices_from_list(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(appendices=["/a.pdf", "/b.pdf"]))
        assert "/a.pdf" in r.appendices
        assert "/b.pdf" in r.appendices

    def test_appendices_from_json_string(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(appendices='["/x.pdf"]'))
        assert "/x.pdf" in r.appendices

    def test_appendices_none_empty(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(appendices=None))
        assert r.appendices == []

    def test_appendices_invalid_json_ignored(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(appendices="{not-json"))
        assert r.appendices == []

    def test_finalized_fields(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 4, 1, tzinfo=timezone.utc)
        r = repo._to_entity(_row(
            status="finalized",
            finalized_by="charlie",
            final_pdf_hash="deadbeef",
            finalized_at=ts,
        ))
        assert r.finalized_by == "charlie"
        assert r.final_pdf_hash == "deadbeef"
        assert r.finalized_at == ts

    def test_modified_by_none(self) -> None:
        repo = self._repo()
        r = repo._to_entity(_row(modified_by=None))
        assert r.modified_by is None

    def test_created_at_datetime_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 1, 15, 8, 30, tzinfo=timezone.utc)
        r = repo._to_entity(_row(created_at=ts))
        assert r.created_at == ts


# ---------------------------------------------------------------------------
# _parse_status static helper
# ---------------------------------------------------------------------------

class TestParseStatus:
    def test_all_valid_values(self) -> None:
        for status in ReportStatus:
            assert PostgreSQLReportRepository._parse_status(status.value) == status

    def test_unknown_falls_back_to_draft(self) -> None:
        assert PostgreSQLReportRepository._parse_status("nonexistent") == ReportStatus.DRAFT


# ---------------------------------------------------------------------------
# UnitOfWork provider selection
# ---------------------------------------------------------------------------

class TestUoWPostgresReportProviderSelection:
    def test_memory_provider_uses_inmemory(self) -> None:
        from infrastructure.persistence.repositories.report_repository import InMemoryReportRepository
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.reports, InMemoryReportRepository)

    def test_sqlite_provider_uses_sqlite(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.sqlite_report_repository import SQLiteReportRepository
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "rep.db"))
        assert isinstance(uow.reports, SQLiteReportRepository)

    @_skip_pg
    def test_postgres_provider_uses_postgres(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.reports, PostgreSQLReportRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (gated by FORENSIC_PG_DSN)
# ---------------------------------------------------------------------------

@_skip_pg
class TestPostgresLiveReportCRUD:
    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_by_id(self) -> None:
        uow = self._uow()
        report = Report.create(id=98801, case_number="PG-RPT-001", created_by="tester")
        report.report_html = "<p>Test content</p>"
        try:
            uow.reports.add(report)
            uow.commit()
            loaded = uow.reports.get_by_id("98801")
            assert loaded is not None
            assert loaded.case_number == "PG-RPT-001"
            assert loaded.report_html == "<p>Test content</p>"
        finally:
            uow.reports.delete("98801")
            uow.commit()

    def test_status_transition_and_reload(self) -> None:
        uow = self._uow()
        report = Report.create(id=98802, case_number="PG-RPT-002", created_by="tester")
        try:
            uow.reports.add(report)
            uow.commit()
            report.submit_for_review("tester")
            uow.reports.update(report)
            uow.commit()
            loaded = uow.reports.get_by_id("98802")
            assert loaded is not None
            assert loaded.status == ReportStatus.IN_REVIEW
        finally:
            uow.reports.delete("98802")
            uow.commit()
