"""application/services/case_service.py - Case service implementation scaffold."""
from __future__ import annotations

from typing import List, Optional

from application.dtos.case_dto import CaseDto, CreateCaseDto, UpdateCaseDto
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_case_repository import ICaseRepository
from application.interfaces.i_case_service import ICaseService
from application.interfaces.i_clock import IClock
from application.services._clock import DefaultClock
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus
from domain.exceptions.domain_exceptions import EntityNotFoundError


class CaseService(ICaseService):
    """Application service orchestrating Case aggregate operations."""

    def __init__(
        self,
        case_repository: ICaseRepository,
        audit_service: IAuditService,
        clock: Optional[IClock] = None,
    ) -> None:
        self._cases = case_repository
        self._audit = audit_service
        self._clock = clock or DefaultClock()

    def get_case(self, case_number: str) -> Optional[CaseDto]:
        case = self._cases.get_by_case_number(case_number)
        if case is None:
            return None
        return self._to_dto(case)

    def get_all_cases(self) -> List[CaseDto]:
        return [self._to_dto(c) for c in self._cases.get_all()]

    def get_cases_by_status(self, status: CaseStatus) -> List[CaseDto]:
        return [self._to_dto(c) for c in self._cases.get_by_status(status)]

    def get_cases_assigned_to(self, username: str) -> List[CaseDto]:
        return [self._to_dto(c) for c in self._cases.get_assigned_to(username)]

    def create_case(self, dto: CreateCaseDto) -> CaseDto:
        case = Case.create(
            case_number=dto.case_number,
            title=dto.title,
            assigned_to=dto.assigned_to,
            created_by=dto.created_by,
            examiner_id=dto.examiner_id,
        )
        case.trial_date = dto.trial_date
        case.sentencing_date = dto.sentencing_date
        case.created_at = self._clock.utcnow()
        case.modified_at = case.created_at
        self._cases.add(case)
        self._audit.log_case_created(
            case_number=case.case_number,
            performed_by=dto.created_by,
            data={
                "title": case.title,
                "assigned_to": case.assigned_to,
            },
        )
        return self._to_dto(case)

    def update_case(self, dto: UpdateCaseDto) -> CaseDto:
        case = self._require_case(dto.case_number)

        if dto.title is not None:
            case.title = dto.title
        if dto.assigned_to is not None:
            case.assigned_to = dto.assigned_to
        if dto.examiner_id is not None:
            case.examiner_id = dto.examiner_id
        if dto.review_comments is not None:
            case.review_comments = dto.review_comments
        if dto.trial_date is not None:
            case.trial_date = dto.trial_date
        if dto.sentencing_date is not None:
            case.sentencing_date = dto.sentencing_date

        case._touch(dto.modified_by or None)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_UPDATED",
            performed_by=dto.modified_by or "system",
            details={"fields": "partial"},
        )
        return self._to_dto(case)

    def delete_case(self, case_number: str, deleted_by: str) -> None:
        # Legacy semantics are soft-delete via archive.
        self.archive_case(case_number, reason="soft-delete", archived_by=deleted_by)

    def transition_status(self, case_number: str, new_status: CaseStatus, changed_by: str) -> CaseDto:
        case = self._require_case(case_number)
        from_status = str(case.status)
        case.transition_to(new_status, changed_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log_case_status_changed(case.case_number, changed_by, from_status, str(new_status))
        return self._to_dto(case)

    def archive_case(self, case_number: str, reason: str, archived_by: str) -> None:
        case = self._require_case(case_number)
        case.archive(archived_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_ARCHIVED",
            performed_by=archived_by,
            details={"reason": reason},
        )

    def restore_case(self, case_number: str, restored_by: str) -> None:
        case = self._require_case(case_number)
        if case.status == CaseStatus.ARCHIVED:
            # Domain currently treats ARCHIVED as terminal. This bridge restore path
            # supports legacy Python archive/restore behaviour until model evolution.
            case.status = CaseStatus.CLOSED
        case.reopen(restored_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_RESTORED",
            performed_by=restored_by,
            details={},
        )

    def search_cases(self, query: str) -> List[CaseDto]:
        return [self._to_dto(c) for c in self._cases.search(query)]

    def get_dashboard_metrics(self) -> dict:
        cases = self._cases.get_all()
        status_counts: dict[str, int] = {}
        for case in cases:
            key = str(case.status)
            status_counts[key] = status_counts.get(key, 0) + 1

        open_cases = sum(1 for c in cases if c.is_open)
        archived_cases = sum(1 for c in cases if c.is_archived)

        return {
            "total_cases": len(cases),
            "open_cases": open_cases,
            "archived_cases": archived_cases,
            "status_counts": status_counts,
            "overdue_legal_processes": sum(c.overdue_legal_count for c in cases),
        }

    # ── Named status transitions ──────────────────────────────────────────

    def submit_case(self, case_number: str, submitted_by: str) -> CaseDto:
        """Submit for review (DRAFT/UNDER_INVESTIGATION → PENDING_REVIEW)."""
        case = self._require_case(case_number)
        case.submit_for_review(submitted_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_SUBMITTED",
            performed_by=submitted_by,
            details={},
        )
        return self._to_dto(case)

    def approve_case(self, case_number: str, approved_by: str) -> CaseDto:
        """Approve for legal review (PENDING_REVIEW → UNDER_LEGAL_REVIEW)."""
        case = self._require_case(case_number)
        case.submit_for_legal_review(approved_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_APPROVED",
            performed_by=approved_by,
            details={},
        )
        return self._to_dto(case)

    def request_revisions(self, case_number: str, comments: str, requested_by: str) -> CaseDto:
        """Send back to investigation with reviewer comments (PENDING_REVIEW → UNDER_INVESTIGATION)."""
        if not comments or not comments.strip():
            from domain.exceptions.domain_exceptions import DomainValidationError
            raise DomainValidationError("comments", "Revision comments are required.")
        case = self._require_case(case_number)
        case.review_comments = comments.strip()
        case.send_back_to_investigation(requested_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_REVISIONS_REQUESTED",
            performed_by=requested_by,
            details={"comments": comments},
        )
        return self._to_dto(case)

    def complete_case(self, case_number: str, completed_by: str) -> CaseDto:
        """Complete case (UNDER_LEGAL_REVIEW → CLOSED)."""
        case = self._require_case(case_number)
        case.close(completed_by)
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_COMPLETED",
            performed_by=completed_by,
            details={},
        )
        return self._to_dto(case)

    def close_case(self, case_number: str, closed_by: str) -> CaseDto:
        """Close case (delegates to complete_case — same terminal state)."""
        return self.complete_case(case_number, closed_by)

    # ── Integrity ─────────────────────────────────────────────────────────

    def set_final_pdf_hash(self, case_number: str, pdf_hash: str, set_by: str) -> None:
        """Record the SHA-256 hash of the final PDF for tamper-evidence."""
        if not pdf_hash or not pdf_hash.strip():
            from domain.exceptions.domain_exceptions import DomainValidationError
            raise DomainValidationError("pdf_hash", "PDF hash cannot be empty.")
        case = self._require_case(case_number)
        case.final_pdf_hash = pdf_hash.strip()
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(
            case_number=case.case_number,
            event_type="CASE_PDF_HASH_SET",
            performed_by=set_by,
            details={"hash": pdf_hash},
        )

    def update_legal_counts(self, case_number: str) -> None:
        """Recalculate and persist pending/overdue legal-process counts."""
        case = self._require_case(case_number)
        # Counts are computed properties on the entity (overdue_legal_count, legal_processes).
        # Persisting just touches the aggregate so the repo re-saves the derived counts.
        case.modified_at = self._clock.utcnow()
        self._cases.update(case)

    def _require_case(self, case_number: str) -> Case:
        case = self._cases.get_by_case_number(case_number)
        if case is None:
            raise EntityNotFoundError("Case", case_number)
        return case

    @staticmethod
    def _to_dto(case: Case) -> CaseDto:
        return CaseDto(
            case_number=case.case_number,
            title=case.title,
            assigned_to=case.assigned_to,
            created_by=case.created_by,
            status=str(case.status),
            examiner_id=case.examiner_id,
            review_comments=case.review_comments or "",
            trial_date=case.trial_date,
            sentencing_date=case.sentencing_date,
            created_at=case.created_at,
            modified_at=case.modified_at,
            modified_by=case.modified_by,
            evidence_count=case.evidence_count,
            open_legal_process_count=len(case.legal_processes),
            overdue_legal_count=case.overdue_legal_count,
            peer_reviewers=list(case.peer_reviewers),
        )
