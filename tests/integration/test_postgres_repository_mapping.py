from __future__ import annotations

from datetime import datetime

from domain.enums.report_status import ReportStatus
from infrastructure.persistence.repositories.postgres_report_repository import PostgreSQLReportRepository
from infrastructure.persistence.repositories.postgres_audit_repository import PostgreSQLAuditRepository


def test_postgres_report_repository_parse_status_fallback() -> None:
    assert PostgreSQLReportRepository._parse_status("draft") == ReportStatus.DRAFT
    assert PostgreSQLReportRepository._parse_status("invalid") == ReportStatus.DRAFT


def test_postgres_audit_repository_details_mapping() -> None:
    repo = PostgreSQLAuditRepository.__new__(PostgreSQLAuditRepository)
    row = {
        "id": 10,
        "case_number": "CASE-PG-1",
        "event_type": "CASE_CREATED",
        "performed_by": "admin",
        "details": '{"k":"v"}',
        "timestamp": datetime.utcnow(),
        "previous_hash": "0" * 64,
        "entry_hash": "1" * 64,
    }

    entity = repo._to_entity(row)
    assert entity.id == 10
    assert entity.details == {"k": "v"}


def test_postgres_audit_repository_details_mapping_none() -> None:
    repo = PostgreSQLAuditRepository.__new__(PostgreSQLAuditRepository)
    row = {
        "id": 11,
        "case_number": "CASE-PG-2",
        "event_type": "CASE_UPDATED",
        "performed_by": "admin",
        "details": None,
        "timestamp": datetime.utcnow(),
        "previous_hash": "0" * 64,
        "entry_hash": "2" * 64,
    }

    entity = repo._to_entity(row)
    assert entity.id == 11
    assert entity.details == {}
