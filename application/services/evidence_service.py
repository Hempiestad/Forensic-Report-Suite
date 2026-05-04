"""application/services/evidence_service.py — EvidenceService (Phase 6)."""
from __future__ import annotations

from typing import List, Optional

from application.dtos.evidence_dto import AddEvidenceDto, EvidenceDto, UpdateEvidenceDto
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_clock import IClock
from application.interfaces.i_evidence_repository import IEvidenceRepository
from application.interfaces.i_evidence_service import IEvidenceService
from application.services._clock import DefaultClock
from domain.entities.evidence import Evidence
from domain.enums.evidence_status import EvidenceStatus
from domain.exceptions.domain_exceptions import DomainValidationError


def _to_dto(ev: Evidence) -> EvidenceDto:
    return EvidenceDto(
        evidence_id=str(ev.id),
        case_number=ev.case_number,
        item_number=ev.evidence_item_number,
        description=ev.physical_description or ev.item_type,
        status=ev.status.value,
        file_path=None,
        hash_value=None,
        hash_algorithm="SHA-256",
        added_by="",
        added_at=ev.created_at,
        imaged_date=ev.imaged_date,
        analyzed_date=ev.analyzed_date,
        completed_date=ev.completed_date,
    )


class EvidenceService(IEvidenceService):
    """Application service for evidence lifecycle management."""

    def __init__(
        self,
        evidence_repository: IEvidenceRepository,
        audit_service: IAuditService,
        clock: Optional[IClock] = None,
    ) -> None:
        self._evidence = evidence_repository
        self._audit = audit_service
        self._clock = clock or DefaultClock()

    def _next_id(self) -> int:
        all_ids = [int(e.id) for e in self._evidence.get_all()]
        return max(all_ids, default=0) + 1

    def _get_or_raise(self, evidence_id: str) -> Evidence:
        ev = self._evidence.get_by_id(evidence_id)
        if ev is None:
            raise DomainValidationError("evidence_id", f"Evidence '{evidence_id}' not found.")
        return ev

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceDto]:
        ev = self._evidence.get_by_id(evidence_id)
        return _to_dto(ev) if ev else None

    def get_evidence_for_case(self, case_number: str) -> List[EvidenceDto]:
        return [_to_dto(e) for e in self._evidence.get_for_case(case_number)]

    # ------------------------------------------------------------------ #
    # Mutations                                                            #
    # ------------------------------------------------------------------ #

    def add_evidence(self, dto: AddEvidenceDto) -> EvidenceDto:
        if not dto.case_number or not dto.case_number.strip():
            raise DomainValidationError("case_number", "Case number is required.")
        if not dto.item_number or not dto.item_number.strip():
            raise DomainValidationError("item_number", "Item number is required.")
        ev = Evidence.create(
            id=self._next_id(),
            case_number=dto.case_number.strip(),
            evidence_item_number=dto.item_number.strip(),
            item_type=dto.description,
        )
        ev.physical_description = dto.description
        ev.created_at = self._clock.utcnow()
        ev.modified_at = ev.created_at
        self._evidence.add(ev)
        self._audit.log_event(
            event_type="EVIDENCE_ADDED",
            description=f"Evidence item '{dto.item_number}' added to case '{dto.case_number}'",
            actor=dto.added_by,
            entity_id=str(ev.id),
            metadata={"case_number": dto.case_number, "item_number": dto.item_number},
        )
        return _to_dto(ev)

    def update_evidence(self, evidence_id: str, dto: UpdateEvidenceDto, updated_by: str) -> EvidenceDto:
        ev = self._get_or_raise(evidence_id)
        if dto.description is not None:
            ev.physical_description = dto.description
            ev.item_type = dto.description
        if dto.physical_description is not None:
            ev.physical_description = dto.physical_description
        if dto.digital_make is not None:
            ev.digital_make = dto.digital_make
        if dto.digital_model is not None:
            ev.digital_model = dto.digital_model
        if dto.digital_serial_number is not None:
            ev.digital_serial_number = dto.digital_serial_number
        if dto.evidence_found is not None:
            ev.evidence_found = dto.evidence_found
        ev.modified_at = self._clock.utcnow()
        self._evidence.update(ev)
        self._audit.log_event(
            event_type="EVIDENCE_UPDATED",
            description=f"Evidence '{evidence_id}' updated",
            actor=updated_by,
            entity_id=evidence_id,
        )
        return _to_dto(ev)

    def remove_evidence(self, evidence_id: str, removed_by: str) -> None:
        ev = self._get_or_raise(evidence_id)
        self._evidence.delete(evidence_id)
        self._audit.log_event(
            event_type="EVIDENCE_REMOVED",
            description=f"Evidence '{evidence_id}' (item {ev.evidence_item_number}) removed",
            actor=removed_by,
            entity_id=evidence_id,
            metadata={"case_number": ev.case_number},
        )

    # ------------------------------------------------------------------ #
    # Status transitions                                                   #
    # ------------------------------------------------------------------ #

    def _transition(self, evidence_id: str, changed_by: str, action: str) -> EvidenceDto:
        ev = self._get_or_raise(evidence_id)
        getattr(ev, action)()
        ev.modified_at = self._clock.utcnow()
        self._evidence.update(ev)
        self._audit.log_event(
            event_type=f"EVIDENCE_{action.upper()}",
            description=f"Evidence '{evidence_id}' transitioned via {action}",
            actor=changed_by,
            entity_id=evidence_id,
            metadata={"new_status": ev.status.value},
        )
        return _to_dto(ev)

    def start_imaging(self, evidence_id: str, changed_by: str) -> EvidenceDto:
        return self._transition(evidence_id, changed_by, "start_imaging")

    def mark_imaged(self, evidence_id: str, changed_by: str) -> EvidenceDto:
        return self._transition(evidence_id, changed_by, "mark_imaged")

    def start_analysis(self, evidence_id: str, changed_by: str) -> EvidenceDto:
        return self._transition(evidence_id, changed_by, "start_analysis")

    def complete_analysis(self, evidence_id: str, changed_by: str) -> EvidenceDto:
        return self._transition(evidence_id, changed_by, "complete_analysis")

    def mark_completed(self, evidence_id: str, changed_by: str) -> EvidenceDto:
        return self._transition(evidence_id, changed_by, "mark_completed")

    def get_digital_evidence_for_case(self, case_number: str) -> List[EvidenceDto]:
        return [
            _to_dto(e)
            for e in self._evidence.get_for_case(case_number)
            if (e.item_type or "").strip().lower() == "digital"
        ]

    def get_incomplete_evidence_for_case(self, case_number: str) -> List[EvidenceDto]:
        from domain.enums.evidence_status import EvidenceStatus
        return [
            _to_dto(e)
            for e in self._evidence.get_for_case(case_number)
            if e.status != EvidenceStatus.COMPLETED
        ]
