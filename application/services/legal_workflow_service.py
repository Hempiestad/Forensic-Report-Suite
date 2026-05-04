"""application/services/legal_workflow_service.py - Legal workflow service scaffold."""
from __future__ import annotations

from typing import List, Optional

from application.dtos.court_date_dto import CourtDateDto, CreateCourtDateDto, UpdateCourtDateDto
from application.dtos.legal_workflow_dto import (
    CreateLegalProcessDto,
    LegalProcessDto,
    UpdateLegalProcessDto,
)
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_case_repository import ICaseRepository
from application.interfaces.i_clock import IClock
from application.interfaces.i_legal_workflow_service import ILegalWorkflowService
from application.services._clock import DefaultClock
from domain.entities.court_date import CourtDate
from domain.entities.legal_process import LegalProcess
from domain.exceptions.domain_exceptions import EntityNotFoundError
from application.interfaces.i_current_user_service import ICurrentUserService
from application.services.current_user_service import SystemUserService


class LegalWorkflowService(ILegalWorkflowService):
    """Coordinates legal-process and court-date workflows on Case aggregates."""

    def __init__(
        self,
        case_repository: ICaseRepository,
        audit_service: IAuditService,
        clock: Optional[IClock] = None,
    ) -> None:
        self._cases = case_repository
        self._audit = audit_service
        self._clock = clock or DefaultClock()
        self._current_user: ICurrentUserService = SystemUserService()

    def with_user(self, current_user: ICurrentUserService) -> "LegalWorkflowService":
        """Fluent setter for the current-user context (used in request-scoped DI)."""
        self._current_user = current_user
        return self

    def get_legal_processes_for_case(self, case_number: str) -> List[LegalProcessDto]:
        case = self._require_case(case_number)
        return [self._to_legal_dto(p) for p in case.legal_processes]

    def add_legal_process(self, case_number: str, dto: CreateLegalProcessDto, added_by: str) -> LegalProcessDto:
        self._current_user.ensure_investigator_access("add_legal_process")
        case = self._require_case(case_number)
        process = LegalProcess(
            id=self._next_process_id(case),
            case_number=case.case_number,
            process_type=dto.process_type,
            due_date=dto.due_date,
        )
        process.created_at = self._clock.utcnow()
        process.modified_at = process.created_at
        case.add_legal_process(process)
        self._cases.update(case)
        self._audit.log_legal_process_added(case.case_number, added_by, dto.process_type)
        return self._to_legal_dto(process)

    def update_legal_process(
        self,
        case_number: str,
        process_id: str,
        dto: UpdateLegalProcessDto,
        updated_by: str,
    ) -> LegalProcessDto:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)

        if dto.process_type is not None:
            process.process_type = dto.process_type
        if dto.due_date is not None:
            process.due_date = dto.due_date
        if dto.status is not None:
            process.status = dto.status

        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_UPDATED", updated_by, {"process_id": process_id})
        return self._to_legal_dto(process)

    def remove_legal_process(self, case_number: str, process_id: str, removed_by: str) -> None:
        self._current_user.ensure_investigator_access("remove_legal_process")
        case = self._require_case(case_number)
        case.remove_legal_process(int(process_id))
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_REMOVED", removed_by, {"process_id": process_id})

    def approve_as_investigator(self, case_number: str, process_id: str, approved_by: str) -> None:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)
        process.approve_investigator(approved_by)
        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_INVESTIGATOR_APPROVED", approved_by, {"process_id": process_id})

    def approve_as_state_attorney(self, case_number: str, process_id: str, approved_by: str) -> None:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)
        process.approve_state_attorney(approved_by)
        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_ATTORNEY_APPROVED", approved_by, {"process_id": process_id})

    def approve_as_judicial(self, case_number: str, process_id: str, approved_by: str) -> None:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)
        process.approve_judicial(approved_by)
        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_JUDICIAL_APPROVED", approved_by, {"process_id": process_id})

    def mark_sent(self, case_number: str, process_id: str, sent_by: str) -> None:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)
        process.mark_sent()
        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_SENT", sent_by, {"process_id": process_id})

    def mark_acknowledged(self, case_number: str, process_id: str, acknowledged_by: str) -> None:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)
        process.mark_acknowledged()
        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_ACKNOWLEDGED", acknowledged_by, {"process_id": process_id})

    def mark_completed(self, case_number: str, process_id: str, completed_by: str) -> None:
        case = self._require_case(case_number)
        process = self._require_process(case, process_id)
        process.mark_completed()
        process.modified_at = self._clock.utcnow()
        self._cases.update(case)
        self._audit.log(case.case_number, "LEGAL_PROCESS_COMPLETED", completed_by, {"process_id": process_id})

    def get_overdue_processes(self) -> List[LegalProcessDto]:
        overdue: List[LegalProcessDto] = []
        for case in self._cases.get_all():
            overdue.extend(self._to_legal_dto(p) for p in case.legal_processes if p.is_overdue)
        return overdue

    def get_processes_due_soon(self, days: int = 7) -> List[LegalProcessDto]:
        upcoming: List[LegalProcessDto] = []
        for case in self._cases.get_all():
            for process in case.legal_processes:
                remaining = process.days_until_due
                if remaining is not None and 0 <= remaining <= days and not process.is_overdue:
                    upcoming.append(self._to_legal_dto(process))
        return upcoming

    def calculate_sla_status(self, process_id: str) -> dict:
        process = self._find_process(process_id)
        if process is None:
            raise EntityNotFoundError("LegalProcess", process_id)
        return {
            "process_id": process_id,
            "is_overdue": process.is_overdue,
            "days_remaining": process.days_until_due,
            "is_fully_approved": process.is_fully_approved,
        }

    def add_court_date(self, case_number: str, dto: CreateCourtDateDto, added_by: str) -> CourtDateDto:
        case = self._require_case(case_number)
        court_date = CourtDate.create(
            id=self._next_court_date_id(case),
            case_number=case.case_number,
            date_type=dto.hearing_type,
            court_date=dto.court_date,
            location=dto.location,
            notes=dto.notes,
        )
        court_date.created_at = self._clock.utcnow()
        case.add_court_date(court_date)
        self._cases.update(case)
        self._audit.log(case.case_number, "COURT_DATE_ADDED", added_by, {"date_type": dto.hearing_type})
        return self._to_court_date_dto(court_date)

    def remove_court_date(self, case_number: str, court_date_id: str, removed_by: str) -> None:
        case = self._require_case(case_number)
        case.remove_court_date(int(court_date_id))
        self._cases.update(case)
        self._audit.log(case.case_number, "COURT_DATE_REMOVED", removed_by, {"court_date_id": court_date_id})

    def get_upcoming_court_dates(self, case_number: Optional[str] = None) -> List[CourtDateDto]:
        case_list = [self._require_case(case_number)] if case_number else self._cases.get_all()
        result: List[CourtDateDto] = []
        for case in case_list:
            result.extend(self._to_court_date_dto(cd) for cd in case.court_dates if cd.is_upcoming)
        return sorted(result, key=lambda x: x.court_date)

    def get_legal_process_by_id(self, process_id: str) -> Optional[LegalProcessDto]:
        process = self._find_process(process_id)
        return self._to_legal_dto(process) if process else None

    def get_pending_processes_for_case(self, case_number: str) -> List[LegalProcessDto]:
        case = self._require_case(case_number)
        terminal_statuses = {"completed", "cancelled"}
        return [
            self._to_legal_dto(p) for p in case.legal_processes
            if str(p.status).lower() not in terminal_statuses
        ]

    def get_court_date_by_id(self, court_date_id: str) -> Optional[CourtDateDto]:
        cid = int(court_date_id)
        for case in self._cases.get_all():
            for cd in case.court_dates:
                if int(cd.id) == cid:
                    return self._to_court_date_dto(cd)
        return None

    def get_all_court_dates_for_case(self, case_number: str) -> List[CourtDateDto]:
        case = self._require_case(case_number)
        return [self._to_court_date_dto(cd) for cd in case.court_dates]

    def get_past_court_dates(self, case_number: Optional[str] = None) -> List[CourtDateDto]:
        case_list = [self._require_case(case_number)] if case_number else self._cases.get_all()
        result: List[CourtDateDto] = []
        for case in case_list:
            result.extend(
                self._to_court_date_dto(cd) for cd in case.court_dates
                if not cd.is_upcoming
            )
        return sorted(result, key=lambda x: x.court_date, reverse=True)

    def update_court_date(
        self,
        case_number: str,
        court_date_id: str,
        dto: UpdateCourtDateDto,
        updated_by: str,
    ) -> CourtDateDto:
        case = self._require_case(case_number)
        cid = int(court_date_id)
        court_date = next((cd for cd in case.court_dates if int(cd.id) == cid), None)
        if court_date is None:
            raise EntityNotFoundError("CourtDate", court_date_id)
        if dto.hearing_type is not None:
            court_date.date_type = dto.hearing_type
        if dto.court_date is not None:
            court_date.court_date = dto.court_date
        if dto.location is not None:
            court_date.location = dto.location
        if dto.notes is not None:
            court_date.notes = dto.notes
        self._cases.update(case)
        self._audit.log(
            case.case_number,
            "COURT_DATE_UPDATED",
            updated_by,
            {"court_date_id": court_date_id},
        )
        return self._to_court_date_dto(court_date)

    def _require_case(self, case_number: str):
        case = self._cases.get_by_case_number(case_number)
        if case is None:
            raise EntityNotFoundError("Case", case_number)
        return case

    @staticmethod
    def _next_process_id(case) -> int:
        if not case.legal_processes:
            return 1
        return max(int(p.id) for p in case.legal_processes) + 1

    @staticmethod
    def _next_court_date_id(case) -> int:
        if not case.court_dates:
            return 1
        return max(int(c.id) for c in case.court_dates) + 1

    @staticmethod
    def _require_process(case, process_id: str) -> LegalProcess:
        pid = int(process_id)
        for process in case.legal_processes:
            if int(process.id) == pid:
                return process
        raise EntityNotFoundError("LegalProcess", process_id)

    def _find_process(self, process_id: str) -> Optional[LegalProcess]:
        pid = int(process_id)
        for case in self._cases.get_all():
            for process in case.legal_processes:
                if int(process.id) == pid:
                    return process
        return None

    @staticmethod
    def _to_legal_dto(process: LegalProcess) -> LegalProcessDto:
        return LegalProcessDto(
            process_id=str(process.id),
            case_number=process.case_number,
            process_type=process.process_type,
            status=process.status,
            created_at=process.created_at,
            created_by=process.investigator_approved_by or "",
            due_date=process.due_date,
            investigator_approved_by=process.investigator_approved_by,
            investigator_approved_at=process.investigator_approved_at,
            state_attorney_approved_by=process.state_attorney_approved_by,
            state_attorney_approved_at=process.state_attorney_approved_at,
            judicial_approved_by=process.judicial_approved_by,
            judicial_approved_at=process.judicial_approved_at,
            sent_at=process.submission_date,
            acknowledged_at=process.received_date,
            completed_at=process.completed_date,
        )

    @staticmethod
    def _to_court_date_dto(court_date: CourtDate) -> CourtDateDto:
        return CourtDateDto(
            court_date_id=str(court_date.id),
            case_number=court_date.case_number,
            hearing_type=court_date.date_type,
            court_date=court_date.court_date,
            location=court_date.location or "",
            notes=court_date.notes or "",
            created_by="",
            created_at=court_date.created_at,
        )
