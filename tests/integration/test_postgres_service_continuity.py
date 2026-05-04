from __future__ import annotations

import os
import uuid

import pytest

from application.dtos.report_dto import CreateReportDto
from application.services.audit_service import AuditService
from application.services.report_service import ReportService
from infrastructure.persistence.unit_of_work import UnitOfWork


def _postgres_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


@pytest.mark.skipif(not _postgres_dsn(), reason="FORENSIC_PG_DSN not set")
def test_postgres_uow_report_and_audit_chain_persists_across_reopen() -> None:
    dsn = _postgres_dsn()
    assert dsn is not None

    case_number = f"CASE-PG-SVC-{uuid.uuid4().hex[:10]}"

    # First run: create and update report, generating audit entries.
    uow1 = UnitOfWork(provider="postgres", postgres_dsn=dsn)
    audit1 = AuditService(uow1.audits)
    report_service1 = ReportService(uow1.reports, audit1)

    created = report_service1.create_report(
        CreateReportDto(case_number=case_number, created_by="admin", initial_html="<p>initial</p>")
    )
    report_service1.update_content(created.report_id, "<p>updated</p>", "admin")
    uow1.commit()

    # Second run: reopen through fresh UoW and verify persistence + chain integrity.
    uow2 = UnitOfWork(provider="postgres", postgres_dsn=dsn)
    audit2 = AuditService(uow2.audits)
    report_service2 = ReportService(uow2.reports, audit2)

    loaded = report_service2.get_report(created.report_id)
    assert loaded is not None
    assert loaded.case_number == case_number

    assert audit2.verify_chain_integrity(case_number) is True
    before = uow2.audits.get_for_case(case_number)
    assert len(before) >= 2

    report_service2.submit_for_review(created.report_id, "admin")
    uow2.commit()

    after = uow2.audits.get_for_case(case_number)
    assert len(after) == len(before) + 1
    assert after[-1].previous_hash == after[-2].entry_hash
    assert audit2.verify_chain_integrity(case_number) is True
