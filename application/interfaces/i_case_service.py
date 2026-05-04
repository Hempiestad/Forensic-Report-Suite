"""application/interfaces/i_case_service.py — Case service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.enums.case_status import CaseStatus


class ICaseService(ABC):

    @abstractmethod
    def get_case(self, case_number: str) -> Optional[object]:
        """Return CaseDto or None."""

    @abstractmethod
    def get_all_cases(self) -> List[object]:
        """Return list of CaseDto."""

    @abstractmethod
    def get_cases_by_status(self, status: CaseStatus) -> List[object]:
        """Return cases filtered by status."""

    @abstractmethod
    def get_cases_assigned_to(self, username: str) -> List[object]:
        """Return cases assigned to a specific user."""

    @abstractmethod
    def create_case(self, dto) -> object:
        """Create a new case. Accepts CreateCaseDto; returns CaseDto."""

    @abstractmethod
    def update_case(self, dto) -> object:
        """Update an existing case. Accepts UpdateCaseDto; returns CaseDto."""

    @abstractmethod
    def delete_case(self, case_number: str, deleted_by: str) -> None:
        """Soft-delete (archive) a case."""

    @abstractmethod
    def transition_status(self, case_number: str, new_status: CaseStatus, changed_by: str) -> object:
        """Apply a status transition, returning updated CaseDto."""

    @abstractmethod
    def archive_case(self, case_number: str, reason: str, archived_by: str) -> None:
        """Archive a case with an audit reason."""

    @abstractmethod
    def restore_case(self, case_number: str, restored_by: str) -> None:
        """Restore a previously archived case."""

    @abstractmethod
    def search_cases(self, query: str) -> List[object]:
        """Full-text search across case fields."""

    @abstractmethod
    def get_dashboard_metrics(self) -> dict:
        """Return aggregate counts/metrics for the dashboard."""

    # ── Named status transitions ──────────────────────────────────────────

    @abstractmethod
    def submit_case(self, case_number: str, submitted_by: str) -> object:
        """Transition case to Pending Review (submission for review)."""

    @abstractmethod
    def approve_case(self, case_number: str, approved_by: str) -> object:
        """Transition case to Under Legal Review (approval)."""

    @abstractmethod
    def request_revisions(self, case_number: str, comments: str, requested_by: str) -> object:
        """Send case back to Under Investigation with mandatory reviewer comments."""

    @abstractmethod
    def complete_case(self, case_number: str, completed_by: str) -> object:
        """Transition case to Closed (completion)."""

    @abstractmethod
    def close_case(self, case_number: str, closed_by: str) -> object:
        """Transition case to Closed terminal state."""

    # ── Integrity / encryption ────────────────────────────────────────────

    @abstractmethod
    def set_final_pdf_hash(self, case_number: str, pdf_hash: str, set_by: str) -> None:
        """Record the SHA-256 hash of the final generated PDF for tamper-evidence."""

    @abstractmethod
    def update_legal_counts(self, case_number: str) -> None:
        """Recalculate and stamp pending/overdue legal-process counts on the case."""
