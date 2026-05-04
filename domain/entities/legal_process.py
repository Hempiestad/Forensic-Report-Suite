"""domain/entities/legal_process.py — Legal process with SLA and approval tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class LegalProcess:
    """Tracks a single legal process (subpoena, warrant, court order, etc.)."""

    # ── Identity ─────────────────────────────────────────────────────────
    id: int
    case_number: str

    # ── Classification ───────────────────────────────────────────────────
    process_type: str          # e.g. "subpoena", "search_warrant", "court_order"
    provider: Optional[str] = None

    # ── Status ───────────────────────────────────────────────────────────
    status: str = "pending"    # pending | sent | acknowledged | completed | cancelled

    # ── Key dates ────────────────────────────────────────────────────────
    submission_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    analysis_start_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    # ── Approval tracking (mirrors Python legal_workflow_helpers) ────────
    investigator_approved: bool = False
    investigator_approved_by: Optional[str] = None
    investigator_approved_at: Optional[datetime] = None

    state_attorney_approved: bool = False
    state_attorney_approved_by: Optional[str] = None
    state_attorney_approved_at: Optional[datetime] = None

    judicial_approved: bool = False
    judicial_approved_by: Optional[str] = None
    judicial_approved_at: Optional[datetime] = None

    # ── Misc ─────────────────────────────────────────────────────────────
    notes: Optional[str] = None
    ndr: bool = False          # No data returned flag

    # ── Audit ────────────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)

    # ================================================================== #
    # Approval workflow                                                    #
    # ================================================================== #

    def approve_investigator(self, approved_by: str) -> None:
        self.investigator_approved = True
        self.investigator_approved_by = approved_by
        self.investigator_approved_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    def approve_state_attorney(self, approved_by: str) -> None:
        self.state_attorney_approved = True
        self.state_attorney_approved_by = approved_by
        self.state_attorney_approved_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    def approve_judicial(self, approved_by: str) -> None:
        self.judicial_approved = True
        self.judicial_approved_by = approved_by
        self.judicial_approved_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    def mark_sent(self, sent_at: Optional[datetime] = None) -> None:
        self.status = "sent"
        self.submission_date = sent_at or datetime.utcnow()
        self.modified_at = datetime.utcnow()

    def mark_acknowledged(self, received_at: Optional[datetime] = None) -> None:
        self.status = "acknowledged"
        self.received_date = received_at or datetime.utcnow()
        self.modified_at = datetime.utcnow()

    def mark_completed(self) -> None:
        self.status = "completed"
        self.completed_date = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    # ================================================================== #
    # SLA helpers                                                          #
    # ================================================================== #

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status in ("completed", "cancelled"):
            return False
        return datetime.utcnow() > self.due_date

    @property
    def days_until_due(self) -> Optional[int]:
        if not self.due_date:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days

    @property
    def is_fully_approved(self) -> bool:
        return (
            self.investigator_approved
            and self.state_attorney_approved
            and self.judicial_approved
        )

    # ================================================================== #
    # Properties                                                           #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return (
            f"LegalProcess(id={self.id}, type={self.process_type!r}, "
            f"status={self.status!r}, overdue={self.is_overdue})"
        )
