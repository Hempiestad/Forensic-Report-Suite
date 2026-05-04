from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from application.dtos.report_dto import CreateReportDto
from application.interfaces.i_report_repository import IReportRepository
from application.services.report_service import ReportService
from domain.entities.report import Report
from domain.enums.report_status import ReportStatus
from domain.exceptions.domain_exceptions import EntityNotFoundError, ReportFinalizedError


class InMemoryReportRepository(IReportRepository):
    def __init__(self) -> None:
        self._items: Dict[str, Report] = {}

    def get_by_id(self, entity_id: str) -> Optional[Report]:
        return self._items.get(entity_id)

    def get_all(self) -> List[Report]:
        return list(self._items.values())

    def add(self, entity: Report) -> None:
        self._items[str(entity.id)] = entity

    def update(self, entity: Report) -> None:
        self._items[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._items.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._items

    def get_for_case(self, case_number: str) -> Optional[Report]:
        for report in self._items.values():
            if report.case_number == case_number:
                return report
        return None

    def get_finalized(self, report_id: str) -> Optional[Report]:
        report = self._items.get(report_id)
        if report and report.status == ReportStatus.FINALIZED:
            return report
        return None


class StubAuditService:
    def __init__(self) -> None:
        self.events: List[dict] = []

    def log(self, case_number: str, event_type: str, performed_by: str, details=None) -> None:
        self.events.append({"type": event_type, "case_number": case_number, "performed_by": performed_by, "details": details or {}})

    def log_report_edited(self, case_number: str, performed_by: str, char_delta: Optional[int] = None) -> None:
        self.events.append({"type": "REPORT_EDITED", "case_number": case_number, "performed_by": performed_by, "char_delta": char_delta})

    def log_report_finalized(self, case_number: str, performed_by: str, pdf_hash: str) -> None:
        self.events.append({"type": "REPORT_FINALIZED", "case_number": case_number, "performed_by": performed_by, "pdf_hash": pdf_hash})


@pytest.fixture
def report_service() -> ReportService:
    return ReportService(InMemoryReportRepository(), StubAuditService())  # type: ignore[arg-type]


def test_report_status_flow(report_service: ReportService) -> None:
    created = report_service.create_report(
        CreateReportDto(case_number="CASE-900", created_by="admin", initial_html="<p>Hello</p>")
    )
    assert created.status == "draft"

    in_review = report_service.submit_for_review(created.report_id, "admin")
    assert in_review.status == "in_review"

    peer = report_service.mark_peer_reviewed(created.report_id, "reviewer", "Looks good")
    assert peer.status == "peer_reviewed"

    finalized = report_service.finalize(created.report_id, "admin")
    assert finalized.status == "finalized"

    report_service.archive_report(created.report_id, "admin")
    archived = report_service.get_report(created.report_id)
    assert archived is not None
    assert archived.status == "archived"


def test_appendix_add_remove(report_service: ReportService) -> None:
    created = report_service.create_report(CreateReportDto(case_number="CASE-901", created_by="admin"))

    report_service.add_appendix(created.report_id, "A.pdf", "admin")
    report_service.add_appendix(created.report_id, "B.pdf", "admin")
    dto = report_service.get_report(created.report_id)
    assert dto is not None
    assert dto.appendix_count == 2

    report_service.remove_appendix(created.report_id, 0, "admin")
    dto = report_service.get_report(created.report_id)
    assert dto is not None
    assert dto.appendix_count == 1


def test_appendix_edit_blocked_after_finalize(report_service: ReportService) -> None:
    created = report_service.create_report(CreateReportDto(case_number="CASE-902", created_by="admin"))
    report_service.submit_for_review(created.report_id, "admin")
    report_service.mark_peer_reviewed(created.report_id, "reviewer", "ok")
    report_service.finalize(created.report_id, "admin")

    with pytest.raises(ReportFinalizedError):
        report_service.add_appendix(created.report_id, "C.pdf", "admin")


def test_missing_report_raises(report_service: ReportService) -> None:
    with pytest.raises(EntityNotFoundError):
        report_service.get_word_count(999)
