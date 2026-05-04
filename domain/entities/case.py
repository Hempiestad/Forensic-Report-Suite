"""
domain/entities/case.py — Case aggregate root.

Design notes:
  - All child collections are encapsulated; callers receive copies.
  - Mutations go through intent methods (add_evidence, transition_to, …).
  - Zero external dependencies — no SQLAlchemy, no Flask, no PyQt5.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.enums.case_status import CaseStatus
from domain.exceptions.domain_exceptions import (
    CaseArchivedError,
    DomainValidationError,
    DuplicateEntityError,
    InvalidStatusTransitionError,
)


@dataclass
class Case:
    """Aggregate root representing a single forensic case."""

    # ── Identity & core fields ───────────────────────────────────────────
    case_number: str
    title: str
    assigned_to: str
    created_by: str

    # ── Status ───────────────────────────────────────────────────────────
    status: CaseStatus = field(default=CaseStatus.DRAFT)

    # ── Optional metadata ────────────────────────────────────────────────
    examiner_id: Optional[str] = None
    review_comments: Optional[str] = None
    trial_date: Optional[datetime] = None
    sentencing_date: Optional[datetime] = None

    # ── Audit fields ─────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None

    # ── Peer review ──────────────────────────────────────────────────────
    peer_reviewers: List[str] = field(default_factory=list)

    # ── Encapsulated child collections (private) ─────────────────────────
    # ── Integrity / encryption ────────────────────────────────────────────
    final_pdf_hash: Optional[str] = None

    # ── Encapsulated child collections (private) ─────────────────────────
    _evidence_items: List = field(default_factory=list, repr=False, compare=False)
    _legal_processes: List = field(default_factory=list, repr=False, compare=False)
    _court_dates: List = field(default_factory=list, repr=False, compare=False)
    _investigative_leads: List = field(default_factory=list, repr=False, compare=False)

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(
        cls,
        case_number: str,
        title: str,
        assigned_to: str,
        created_by: str,
        examiner_id: Optional[str] = None,
    ) -> "Case":
        """Factory method — validates inputs and returns a new DRAFT case."""
        if not case_number or not case_number.strip():
            raise DomainValidationError("case_number", "Case number cannot be empty.")
        if not assigned_to or not assigned_to.strip():
            raise DomainValidationError("assigned_to", "Assigned user cannot be empty.")
        if not created_by or not created_by.strip():
            raise DomainValidationError("created_by", "Creator cannot be empty.")

        return cls(
            case_number=case_number.strip(),
            title=(title.strip() if title else case_number.strip()),
            assigned_to=assigned_to.strip(),
            created_by=created_by.strip(),
            examiner_id=examiner_id,
        )

    # ================================================================== #
    # Status transitions                                                   #
    # ================================================================== #

    def transition_to(self, new_status: CaseStatus, changed_by: str) -> None:
        """Validate and apply a status transition."""
        if self.status == CaseStatus.ARCHIVED:
            raise CaseArchivedError(self.case_number)
        if not self.status.can_transition_to(new_status):
            raise InvalidStatusTransitionError(
                self.case_number, str(self.status), str(new_status)
            )
        self.status = new_status
        self._touch(changed_by)

    def open_investigation(self, changed_by: str) -> None:
        self.transition_to(CaseStatus.UNDER_INVESTIGATION, changed_by)

    def submit_for_review(self, changed_by: str) -> None:
        self.transition_to(CaseStatus.PENDING_REVIEW, changed_by)

    def submit_for_legal_review(self, changed_by: str) -> None:
        self.transition_to(CaseStatus.UNDER_LEGAL_REVIEW, changed_by)

    def close(self, changed_by: str) -> None:
        self.transition_to(CaseStatus.CLOSED, changed_by)

    def archive(self, changed_by: str) -> None:
        self.transition_to(CaseStatus.ARCHIVED, changed_by)

    def reopen(self, changed_by: str) -> None:
        """Re-open a closed case into investigation."""
        self.transition_to(CaseStatus.UNDER_INVESTIGATION, changed_by)

    def send_back_to_investigation(self, changed_by: str) -> None:
        self.transition_to(CaseStatus.UNDER_INVESTIGATION, changed_by)

    # ================================================================== #
    # Evidence items (encapsulated collection)                             #
    # ================================================================== #

    @property
    def evidence_items(self) -> List:
        return list(self._evidence_items)

    def add_evidence(self, evidence) -> None:
        self._guard_archived()
        if any(e.id == getattr(evidence, "id", None) for e in self._evidence_items):
            raise DuplicateEntityError("Evidence", evidence.id)
        self._evidence_items.append(evidence)
        self._touch()

    def remove_evidence(self, evidence_id: int) -> None:
        self._guard_archived()
        self._evidence_items = [e for e in self._evidence_items if e.id != evidence_id]
        self._touch()

    def get_evidence(self, evidence_id: int):
        return next((e for e in self._evidence_items if e.id == evidence_id), None)

    # ================================================================== #
    # Legal processes (encapsulated collection)                            #
    # ================================================================== #

    @property
    def legal_processes(self) -> List:
        return list(self._legal_processes)

    def add_legal_process(self, process) -> None:
        self._guard_archived()
        self._legal_processes.append(process)
        self._touch()

    def remove_legal_process(self, process_id: int) -> None:
        self._guard_archived()
        self._legal_processes = [p for p in self._legal_processes if p.id != process_id]
        self._touch()

    # ================================================================== #
    # Court dates (encapsulated collection)                                #
    # ================================================================== #

    @property
    def court_dates(self) -> List:
        return list(self._court_dates)

    def add_court_date(self, court_date) -> None:
        self._guard_archived()
        self._court_dates.append(court_date)
        self._touch()

    def remove_court_date(self, date_id: int) -> None:
        self._guard_archived()
        self._court_dates = [d for d in self._court_dates if d.id != date_id]
        self._touch()

    # ================================================================== #
    # Investigative leads (encapsulated collection)                        #
    # ================================================================== #

    @property
    def investigative_leads(self) -> List:
        return list(self._investigative_leads)

    def add_investigative_lead(self, lead) -> None:
        self._guard_archived()
        self._investigative_leads.append(lead)
        self._touch()

    def remove_investigative_lead(self, lead_id: int) -> None:
        self._guard_archived()
        self._investigative_leads = [l for l in self._investigative_leads if l.id != lead_id]  # noqa: E741
        self._touch()

    # ================================================================== #
    # Computed properties                                                  #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return self.case_number

    @property
    def is_archived(self) -> bool:
        return self.status == CaseStatus.ARCHIVED

    @property
    def is_closed(self) -> bool:
        return self.status in (CaseStatus.CLOSED, CaseStatus.ARCHIVED)

    @property
    def is_open(self) -> bool:
        return self.status.is_open

    @property
    def has_open_legal_processes(self) -> bool:
        closed = {"completed", "cancelled"}
        return any(
            getattr(p, "status", None) not in closed for p in self._legal_processes
        )

    @property
    def overdue_legal_count(self) -> int:
        now = datetime.utcnow()
        closed = {"completed", "cancelled"}
        return sum(
            1
            for p in self._legal_processes
            if getattr(p, "due_date", None)
            and p.due_date < now
            and getattr(p, "status", None) not in closed
        )

    @property
    def evidence_count(self) -> int:
        return len(self._evidence_items)

    # ================================================================== #
    # Internal helpers                                                     #
    # ================================================================== #

    def _touch(self, changed_by: Optional[str] = None) -> None:
        self.modified_at = datetime.utcnow()
        if changed_by:
            self.modified_by = changed_by

    def _guard_archived(self) -> None:
        if self.is_archived:
            raise CaseArchivedError(self.case_number)

    def __repr__(self) -> str:
        return f"Case(case_number={self.case_number!r}, status={self.status!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Case):
            return NotImplemented
        return self.case_number == other.case_number

    def __hash__(self) -> int:
        return hash(self.case_number)
