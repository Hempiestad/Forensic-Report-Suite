"""application/services/report_service.py - Report service implementation scaffold."""
from __future__ import annotations

from typing import Optional

from application.dtos.report_dto import CreateReportDto, ReportDto
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_clock import IClock
from application.interfaces.i_report_repository import IReportRepository
from application.interfaces.i_report_service import IReportService
from application.services._clock import DefaultClock
from domain.entities.report import Report
from domain.enums.report_status import ReportStatus
from domain.exceptions.domain_exceptions import EntityNotFoundError


class ReportService(IReportService):
    """Application service orchestrating Report aggregate workflows."""

    def __init__(
        self,
        report_repository: IReportRepository,
        audit_service: IAuditService,
        clock: Optional[IClock] = None,
    ) -> None:
        self._reports = report_repository
        self._audit = audit_service
        self._clock = clock or DefaultClock()

    def get_report(self, report_id: int) -> Optional[ReportDto]:
        report = self._reports.get_by_id(str(report_id))
        if report is None:
            return None
        return self._to_dto(report)

    def get_report_for_case(self, case_number: str) -> Optional[ReportDto]:
        report = self._reports.get_for_case(case_number)
        if report is None:
            return None
        return self._to_dto(report)

    def create_report(self, dto: CreateReportDto) -> ReportDto:
        report = Report.create(
            id=self._next_id(),
            case_number=dto.case_number,
            created_by=dto.created_by,
        )
        report.created_at = self._clock.utcnow()
        report.modified_at = report.created_at
        if dto.initial_html:
            report.update_content(dto.initial_html, dto.created_by)
            report.modified_at = self._clock.utcnow()
        self._reports.add(report)
        self._audit.log(
            case_number=report.case_number,
            event_type="REPORT_CREATED",
            performed_by=dto.created_by,
            details={"report_id": report.id},
        )
        return self._to_dto(report)

    def update_content(self, report_id: int, html_content: str, updated_by: str) -> ReportDto:
        report = self._require_report(report_id)
        previous_count = report.word_count
        report.update_content(html_content, updated_by)
        report.modified_at = self._clock.utcnow()
        self._reports.update(report)
        self._audit.log_report_edited(report.case_number, updated_by, report.word_count - previous_count)
        return self._to_dto(report)

    def submit_for_review(self, report_id: int, submitted_by: str) -> ReportDto:
        report = self._require_report(report_id)
        report.submit_for_review(submitted_by)
        report.modified_at = self._clock.utcnow()
        self._reports.update(report)
        self._audit.log(report.case_number, "REPORT_SUBMITTED_FOR_REVIEW", submitted_by, {"report_id": report.id})
        return self._to_dto(report)

    def mark_peer_reviewed(self, report_id: int, reviewed_by: str, comments: str) -> ReportDto:
        report = self._require_report(report_id)
        report.mark_peer_reviewed(reviewed_by)
        report.modified_at = self._clock.utcnow()
        self._reports.update(report)
        self._audit.log(
            report.case_number,
            "REPORT_PEER_REVIEWED",
            reviewed_by,
            {"report_id": report.id, "comments": comments},
        )
        return self._to_dto(report)

    def finalize(self, report_id: int, finalized_by: str) -> ReportDto:
        report = self._require_report(report_id)
        report.finalize(finalized_by)
        report.finalized_at = self._clock.utcnow()
        report.modified_at = report.finalized_at
        self._reports.update(report)
        self._audit.log_report_finalized(report.case_number, finalized_by, report.final_pdf_hash or "")
        return self._to_dto(report)

    def archive_report(self, report_id: int, archived_by: str) -> None:
        report = self._require_report(report_id)
        report.transition_to(ReportStatus.ARCHIVED, archived_by)
        report.modified_at = self._clock.utcnow()
        self._reports.update(report)
        self._audit.log(report.case_number, "REPORT_ARCHIVED", archived_by, {"report_id": report.id})

    def add_appendix(self, report_id: int, appendix: str, added_by: str) -> None:
        report = self._require_report(report_id)
        report.add_appendix(appendix, added_by)
        report.modified_at = self._clock.utcnow()
        self._reports.update(report)
        self._audit.log(report.case_number, "REPORT_APPENDIX_ADDED", added_by, {"report_id": report.id})

    def remove_appendix(self, report_id: int, appendix_index: int, removed_by: str) -> None:
        report = self._require_report(report_id)
        appendices = report.appendices
        if appendix_index < 0 or appendix_index >= len(appendices):
            return
        report.remove_appendix(appendices[appendix_index], removed_by)
        report.modified_at = self._clock.utcnow()
        self._reports.update(report)
        self._audit.log(report.case_number, "REPORT_APPENDIX_REMOVED", removed_by, {"report_id": report.id})

    def export_to_docx(self, report_id: int, output_path: str) -> None:
        raise NotImplementedError("Report DOCX export wiring is scheduled for Phase 4.")

    def export_to_pdf(self, report_id: int, output_path: str) -> None:
        raise NotImplementedError("Report PDF export wiring is scheduled for Phase 4.")

    def get_word_count(self, report_id: int) -> int:
        report = self._require_report(report_id)
        return report.word_count

    def _require_report(self, report_id: int) -> Report:
        report = self._reports.get_by_id(str(report_id))
        if report is None:
            raise EntityNotFoundError("Report", report_id)
        return report

    def _next_id(self) -> int:
        existing = self._reports.get_all()
        if not existing:
            return 1
        return max(int(r.id) for r in existing) + 1

    @staticmethod
    def _to_dto(report: Report) -> ReportDto:
        return ReportDto(
            report_id=report.id,
            case_number=report.case_number,
            status=str(report.status),
            created_by=report.created_by or "",
            created_at=report.created_at,
            modified_at=report.modified_at,
            modified_by=report.modified_by,
            finalized_by=report.finalized_by,
            finalized_at=report.finalized_at,
            final_pdf_hash=report.final_pdf_hash,
            word_count=report.word_count,
            appendix_count=len(report.appendices),
        )
