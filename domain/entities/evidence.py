"""domain/entities/evidence.py — Evidence item with status state machine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.enums.evidence_status import EvidenceStatus
from domain.exceptions.domain_exceptions import (
    DomainValidationError,
    InvalidStatusTransitionError,
)


@dataclass
class Evidence:
    """Represents a single piece of evidence attached to a case."""

    # ── Identity ─────────────────────────────────────────────────────────
    id: int
    case_number: str
    evidence_item_number: str

    # ── Classification ───────────────────────────────────────────────────
    item_type: str
    physical_description: Optional[str] = None

    # ── Digital device details ───────────────────────────────────────────
    digital_make: Optional[str] = None
    digital_model: Optional[str] = None
    digital_type: Optional[str] = None
    digital_serial_number: Optional[str] = None
    digital_storage_size: Optional[str] = None
    password: Optional[str] = None

    # ── Status ───────────────────────────────────────────────────────────
    status: EvidenceStatus = field(default=EvidenceStatus.NOT_IMAGED)

    # ── Key dates ────────────────────────────────────────────────────────
    imaged_date: Optional[datetime] = None
    analyzed_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    # ── Findings summary ─────────────────────────────────────────────────
    evidence_found: Optional[str] = None

    # ── Audit ────────────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(
        cls,
        id: int,
        case_number: str,
        evidence_item_number: str,
        item_type: str,
    ) -> "Evidence":
        if not case_number:
            raise DomainValidationError("case_number", "Case number is required.")
        if not evidence_item_number:
            raise DomainValidationError("evidence_item_number", "Item number is required.")
        if not item_type:
            raise DomainValidationError("item_type", "Item type is required.")
        return cls(
            id=id,
            case_number=case_number,
            evidence_item_number=evidence_item_number,
            item_type=item_type,
        )

    # ================================================================== #
    # Status transitions                                                   #
    # ================================================================== #

    def transition_to(self, new_status: EvidenceStatus) -> None:
        if not self.status.can_transition_to(new_status):
            raise InvalidStatusTransitionError(
                str(self.id), str(self.status), str(new_status)
            )
        self.status = new_status
        self.modified_at = datetime.utcnow()
        # Stamp relevant date fields automatically
        if new_status == EvidenceStatus.IMAGED and not self.imaged_date:
            self.imaged_date = datetime.utcnow()
        elif new_status == EvidenceStatus.ANALYSIS_COMPLETE and not self.analyzed_date:
            self.analyzed_date = datetime.utcnow()
        elif new_status == EvidenceStatus.COMPLETED and not self.completed_date:
            self.completed_date = datetime.utcnow()

    def start_imaging(self) -> None:
        self.transition_to(EvidenceStatus.IMAGING_IN_PROGRESS)

    def mark_imaged(self) -> None:
        self.transition_to(EvidenceStatus.IMAGED)

    def start_analysis(self) -> None:
        self.transition_to(EvidenceStatus.ANALYSIS_IN_PROGRESS)

    def complete_analysis(self) -> None:
        self.transition_to(EvidenceStatus.ANALYSIS_COMPLETE)

    def mark_completed(self) -> None:
        self.transition_to(EvidenceStatus.COMPLETED)

    # ================================================================== #
    # Properties                                                           #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return str(self.id)

    @property
    def is_completed(self) -> bool:
        return self.status == EvidenceStatus.COMPLETED

    def __repr__(self) -> str:
        return f"Evidence(id={self.id}, item_number={self.evidence_item_number!r}, status={self.status!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Evidence):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
