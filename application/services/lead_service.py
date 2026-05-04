"""application/services/lead_service.py — InvestigativeLeadService (Phase 11)."""
from __future__ import annotations

from typing import List, Optional

from application.dtos.lead_dto import CreateLeadDto, LeadDto, UpdateLeadDto
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_clock import IClock
from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
from application.interfaces.i_lead_service import IInvestigativeLeadService
from application.services._clock import DefaultClock
from domain.entities.investigative_lead import InvestigativeLead
from domain.exceptions.domain_exceptions import DomainValidationError
from application.interfaces.i_current_user_service import ICurrentUserService
from application.services.current_user_service import SystemUserService


def _to_dto(lead: InvestigativeLead) -> LeadDto:
    return LeadDto(
        lead_id=str(lead.id),
        case_number=lead.case_number,
        name=lead.name,
        source=lead.source,
        description=lead.description,
        completed=lead.completed,
        completed_at=lead.completed_at,
        completed_by=lead.completed_by,
        created_at=lead.created_at,
        modified_at=lead.modified_at,
    )


class InvestigativeLeadService(IInvestigativeLeadService):
    """Application service for investigative lead management."""

    def __init__(
        self,
        lead_repository: IInvestigativeLeadRepository,
        audit_service: IAuditService,
        clock: Optional[IClock] = None,
    ) -> None:
        self._leads = lead_repository
        self._audit = audit_service
        self._clock = clock or DefaultClock()
        self._current_user: ICurrentUserService = SystemUserService()

    def with_user(self, current_user: ICurrentUserService) -> "InvestigativeLeadService":
        """Fluent setter for the current-user context (used in request-scoped DI)."""
        self._current_user = current_user
        return self

    def _next_id(self) -> int:
        all_ids = [int(l.id) for l in self._leads.get_all()]
        return max(all_ids, default=0) + 1

    def _get_or_raise(self, lead_id: str) -> InvestigativeLead:
        lead = self._leads.get_by_id(str(lead_id))
        if lead is None:
            raise DomainValidationError("lead_id", f"Lead '{lead_id}' not found.")
        return lead

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get_lead(self, lead_id: str) -> Optional[LeadDto]:
        lead = self._leads.get_by_id(str(lead_id))
        return _to_dto(lead) if lead else None

    def get_leads_for_case(self, case_number: str) -> List[LeadDto]:
        return [_to_dto(l) for l in self._leads.get_for_case(case_number)]

    def get_open_leads_for_case(self, case_number: str) -> List[LeadDto]:
        return [_to_dto(l) for l in self._leads.get_open_for_case(case_number)]

    # ------------------------------------------------------------------ #
    # Mutations                                                            #
    # ------------------------------------------------------------------ #

    def create_lead(self, dto: CreateLeadDto) -> LeadDto:
        self._current_user.ensure_investigator_access("create_lead")
        if not dto.case_number or not dto.case_number.strip():
            raise DomainValidationError("case_number", "Case number is required.")
        if not dto.name or not dto.name.strip():
            raise DomainValidationError("name", "Lead name is required.")
        now = self._clock.utcnow()
        lead = InvestigativeLead.create(
            id=self._next_id(),
            case_number=dto.case_number.strip(),
            name=dto.name.strip(),
            source=dto.source,
            description=dto.description,
        )
        lead.created_at = now
        lead.modified_at = now
        self._leads.add(lead)
        self._audit.log_event(
            event_type="LEAD_CREATED",
            description=f"Lead '{lead.name}' created for case '{lead.case_number}'",
            actor=dto.created_by,
            entity_id=str(lead.id),
            metadata={"case_number": lead.case_number},
        )
        return _to_dto(lead)

    def update_lead(self, dto: UpdateLeadDto) -> LeadDto:
        self._current_user.ensure_investigator_access("update_lead")
        lead = self._get_or_raise(dto.lead_id)
        if dto.name is not None:
            if not dto.name.strip():
                raise DomainValidationError("name", "Lead name cannot be empty.")
            lead.name = dto.name.strip()
        if dto.source is not None:
            lead.source = dto.source
        if dto.description is not None:
            lead.description = dto.description
        lead.modified_at = self._clock.utcnow()
        self._leads.update(lead)
        self._audit.log_event(
            event_type="LEAD_UPDATED",
            description=f"Lead '{lead.name}' updated",
            actor=dto.modified_by,
            entity_id=str(lead.id),
            metadata={"case_number": lead.case_number},
        )
        return _to_dto(lead)

    def complete_lead(self, lead_id: str, completed_by: str) -> LeadDto:
        self._current_user.ensure_investigator_access("complete_lead")
        lead = self._get_or_raise(lead_id)
        if lead.completed:
            raise DomainValidationError("lead_id", f"Lead '{lead_id}' is already completed.")
        lead.mark_completed(completed_by)
        lead.completed_at = self._clock.utcnow()
        lead.modified_at = self._clock.utcnow()
        self._leads.update(lead)
        self._audit.log_event(
            event_type="LEAD_COMPLETED",
            description=f"Lead '{lead.name}' marked completed",
            actor=completed_by,
            entity_id=str(lead.id),
            metadata={"case_number": lead.case_number},
        )
        return _to_dto(lead)

    def reopen_lead(self, lead_id: str, reopened_by: str) -> LeadDto:
        self._current_user.ensure_investigator_access("reopen_lead")
        lead = self._get_or_raise(lead_id)
        if not lead.completed:
            raise DomainValidationError("lead_id", f"Lead '{lead_id}' is not completed.")
        lead.reopen()
        lead.modified_at = self._clock.utcnow()
        self._leads.update(lead)
        self._audit.log_event(
            event_type="LEAD_REOPENED",
            description=f"Lead '{lead.name}' reopened",
            actor=reopened_by,
            entity_id=str(lead.id),
            metadata={"case_number": lead.case_number},
        )
        return _to_dto(lead)

    def delete_lead(self, lead_id: str, deleted_by: str) -> None:
        self._current_user.ensure_investigator_access("delete_lead")
        lead = self._get_or_raise(lead_id)
        self._leads.delete(str(lead.id))
        self._audit.log_event(
            event_type="LEAD_DELETED",
            description=f"Lead '{lead.name}' deleted",
            actor=deleted_by,
            entity_id=str(lead.id),
            metadata={"case_number": lead.case_number},
        )
