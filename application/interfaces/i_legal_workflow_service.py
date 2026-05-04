"""application/interfaces/i_legal_workflow_service.py — Legal workflow service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class ILegalWorkflowService(ABC):

    # ── Processes ────────────────────────────────────────────────────────

    @abstractmethod
    def get_legal_processes_for_case(self, case_number: str) -> List[object]:
        """Return list of LegalProcessDto for a case."""

    @abstractmethod
    def add_legal_process(self, case_number: str, dto, added_by: str) -> object:
        """Add a new legal process to a case. Returns LegalProcessDto."""

    @abstractmethod
    def update_legal_process(self, case_number: str, process_id: str, dto, updated_by: str) -> object:
        """Update an existing legal process."""

    @abstractmethod
    def remove_legal_process(self, case_number: str, process_id: str, removed_by: str) -> None:
        """Remove a legal process from a case."""

    # ── Approvals ────────────────────────────────────────────────────────

    @abstractmethod
    def approve_as_investigator(self, case_number: str, process_id: str, approved_by: str) -> None:
        """Record investigator approval step."""

    @abstractmethod
    def approve_as_state_attorney(self, case_number: str, process_id: str, approved_by: str) -> None:
        """Record state-attorney approval step."""

    @abstractmethod
    def approve_as_judicial(self, case_number: str, process_id: str, approved_by: str) -> None:
        """Record judicial approval step."""

    @abstractmethod
    def mark_sent(self, case_number: str, process_id: str, sent_by: str) -> None:
        """Mark a legal process as sent to the relevant party."""

    @abstractmethod
    def mark_acknowledged(self, case_number: str, process_id: str, acknowledged_by: str) -> None:
        """Mark a legal process as acknowledged by the recipient."""

    @abstractmethod
    def mark_completed(self, case_number: str, process_id: str, completed_by: str) -> None:
        """Close out a legal process."""

    # ── SLA / reporting ──────────────────────────────────────────────────

    @abstractmethod
    def get_overdue_processes(self) -> List[object]:
        """Return all legal processes past their SLA due date."""

    @abstractmethod
    def get_processes_due_soon(self, days: int = 7) -> List[object]:
        """Return processes whose SLA expires within N days."""

    @abstractmethod
    def calculate_sla_status(self, process_id: str) -> dict:
        """Return SLA status dict with is_overdue, days_remaining fields."""

    # ── Court dates ──────────────────────────────────────────────────────

    @abstractmethod
    def add_court_date(self, case_number: str, dto, added_by: str) -> object:
        """Add a court date to a case."""

    @abstractmethod
    def remove_court_date(self, case_number: str, court_date_id: str, removed_by: str) -> None:
        """Remove a court date from a case."""

    @abstractmethod
    def get_upcoming_court_dates(self, case_number: Optional[str] = None) -> List[object]:
        """Return upcoming court dates, optionally filtered by case."""

    @abstractmethod
    def get_legal_process_by_id(self, process_id: str) -> Optional[object]:
        """Return LegalProcessDto for a specific process_id, or None if not found."""

    @abstractmethod
    def get_pending_processes_for_case(self, case_number: str) -> List[object]:
        """Return legal processes that are not yet completed (pending/submitted)."""

    @abstractmethod
    def get_court_date_by_id(self, court_date_id: str) -> Optional[object]:
        """Return CourtDateDto for a specific court_date_id, or None if not found."""

    @abstractmethod
    def get_all_court_dates_for_case(self, case_number: str) -> List[object]:
        """Return all court dates for a case regardless of past/future."""

    @abstractmethod
    def get_past_court_dates(self, case_number: Optional[str] = None) -> List[object]:
        """Return court dates in the past, optionally scoped to one case."""

    @abstractmethod
    def update_court_date(
        self, case_number: str, court_date_id: str, dto, updated_by: str
    ) -> object:
        """Update an existing court date. Returns updated CourtDateDto."""
