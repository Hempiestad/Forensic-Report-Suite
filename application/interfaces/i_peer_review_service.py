"""application/interfaces/i_peer_review_service.py - Peer review service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IPeerReviewService(ABC):

    @abstractmethod
    def export_report_for_review(self, report_id: int, exported_by: str, output_path: str) -> str:
        """Export a report package for peer review and return output path."""

    @abstractmethod
    def import_reviewed_report(self, report_id: int, import_path: str, imported_by: str) -> dict:
        """Import a reviewed report package and return summary metadata."""

    @abstractmethod
    def add_comment(self, report_id: int, location_ref: str, comment: str, commented_by: str) -> None:
        """Add an inline peer review comment."""

    @abstractmethod
    def get_comments(self, report_id: int) -> List[dict]:
        """Return peer review comments for a report."""

    @abstractmethod
    def mark_sign_off(self, report_id: int, reviewer_username: str, approved: bool, notes: str = "") -> None:
        """Record reviewer sign-off decision."""

    @abstractmethod
    def get_review_summary(self, report_id: int) -> dict:
        """Return aggregate peer review summary data."""
