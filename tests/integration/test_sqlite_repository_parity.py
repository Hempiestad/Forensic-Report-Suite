from __future__ import annotations

from datetime import datetime
from pathlib import Path

from application.dtos.report_dto import CreateReportDto
from application.services.audit_service import AuditService
from application.services.report_service import ReportService
from domain.entities.audit_entry import AuditEntry
from domain.entities.notification import Notification
from domain.entities.report import Report
from domain.entities.template import Template
from domain.enums.notification_type import NotificationType
from domain.enums.report_status import ReportStatus
from domain.enums.template_category import TemplateCategory
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
from infrastructure.persistence.repositories.sqlite_notification_repository import SQLiteNotificationRepository
from infrastructure.persistence.repositories.sqlite_report_repository import SQLiteReportRepository
from infrastructure.persistence.repositories.sqlite_template_repository import SQLiteTemplateRepository
from infrastructure.persistence.unit_of_work import UnitOfWork


def _sqlite_ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "sqlite_parity.db"))


def test_sqlite_report_repository_crud(tmp_path: Path) -> None:
    ctx = _sqlite_ctx(tmp_path)
    repo = SQLiteReportRepository(ctx)

    report = Report.create(1, "CASE-R-1", "admin")
    report.report_html = "<p>hello</p>"
    repo.add(report)
    ctx.commit()

    loaded = repo.get_by_id("1")
    assert loaded is not None
    assert loaded.case_number == "CASE-R-1"

    loaded.submit_for_review("admin")
    loaded.mark_peer_reviewed("reviewer")
    loaded.finalize("admin", "hash1")
    repo.update(loaded)
    ctx.commit()

    finalized = repo.get_finalized("1")
    assert finalized is not None
    assert finalized.status == ReportStatus.FINALIZED


def test_sqlite_audit_repository_persists_chain(tmp_path: Path) -> None:
    ctx = _sqlite_ctx(tmp_path)
    repo = SQLiteAuditRepository(ctx)

    e1 = AuditEntry.create("CASE-A-1", "CASE_CREATED", "admin", {"ok": True})
    repo.add(e1)
    e2 = AuditEntry.create("CASE-A-1", "CASE_UPDATED", "admin", {"ok": True}, previous_hash=e1.entry_hash)
    repo.add(e2)
    ctx.commit()

    reloaded = SQLiteAuditRepository(SQLiteDbContext(str(tmp_path / "sqlite_parity.db")))
    entries = reloaded.get_for_case("CASE-A-1")
    assert len(entries) == 2
    assert entries[1].previous_hash == entries[0].entry_hash


def test_sqlite_template_repository_crud(tmp_path: Path) -> None:
    ctx = _sqlite_ctx(tmp_path)
    repo = SQLiteTemplateRepository(ctx)

    tmpl = Template.create(
        id=10,
        name="Memo Template",
        category=TemplateCategory.MEMO,
        html_content="<p>{name}</p>",
        created_by="admin",
        description="memo desc",
    )
    tmpl.publish("admin")
    tmpl.tags = ["memo", "internal"]
    repo.add(tmpl)
    ctx.commit()

    by_name = repo.get_by_name("Memo Template")
    assert by_name is not None
    assert by_name.is_published is True

    by_category = repo.get_by_category("memo")
    assert len(by_category) == 1


def test_sqlite_notification_repository_queries(tmp_path: Path) -> None:
    ctx = _sqlite_ctx(tmp_path)
    repo = SQLiteNotificationRepository(ctx)

    n1 = Notification.create(1, NotificationType.CASE_CREATED, "det.a", "t1", "m1")
    n2 = Notification.create(2, NotificationType.CASE_STATUS_CHANGE, "det.a", "t2", "m2")
    n3 = Notification.create(3, NotificationType.SYSTEM, "det.b", "t3", "m3")
    repo.add(n1)
    repo.add(n2)
    repo.add(n3)
    ctx.commit()

    for_user = repo.get_for_user("det.a")
    assert len(for_user) == 2
    assert repo.get_unread_count("det.a") == 2

    marked = repo.mark_all_as_read("det.a")
    assert marked == 2
    assert repo.get_unread_count("det.a") == 0


def test_sqlite_uow_report_and_audit_chain_persists_across_reopen(tmp_path: Path) -> None:
    db_path = str(tmp_path / "sqlite_uow_services.db")

    # First process lifecycle writes report + audit entries.
    uow1 = UnitOfWork(provider="sqlite", sqlite_db_path=db_path)
    audit1 = AuditService(uow1.audits)
    report_service1 = ReportService(uow1.reports, audit1)

    created = report_service1.create_report(
        CreateReportDto(case_number="CASE-SVC-1", created_by="admin", initial_html="<p>hello</p>")
    )
    report_service1.update_content(created.report_id, "<p>updated once</p>", "admin")
    uow1.commit()

    # Reopen through a fresh UnitOfWork to prove persistence across restart.
    uow2 = UnitOfWork(provider="sqlite", sqlite_db_path=db_path)
    audit2 = AuditService(uow2.audits)
    report_service2 = ReportService(uow2.reports, audit2)

    loaded = report_service2.get_report(created.report_id)
    assert loaded is not None
    assert loaded.case_number == "CASE-SVC-1"

    # Chain exists and remains valid after reopen.
    assert audit2.verify_chain_integrity("CASE-SVC-1") is True
    entries_before = uow2.audits.get_for_case("CASE-SVC-1")
    assert len(entries_before) >= 2

    # Continue workflow and ensure chain continuity appends correctly.
    report_service2.submit_for_review(created.report_id, "admin")
    uow2.commit()

    entries_after = uow2.audits.get_for_case("CASE-SVC-1")
    assert len(entries_after) == len(entries_before) + 1
    assert entries_after[-1].previous_hash == entries_after[-2].entry_hash
    assert audit2.verify_chain_integrity("CASE-SVC-1") is True
