"""application/interfaces/i_report_service.py — Report service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IReportService(ABC):

    @abstractmethod
    def get_report(self, report_id: int) -> Optional[object]:
        """Return ReportDto or None."""

    @abstractmethod
    def get_report_for_case(self, case_number: str) -> Optional[object]:
        """Return the report associated with a case, or None."""

    @abstractmethod
    def create_report(self, dto) -> object:
        """Create a blank or template-seeded report. Returns ReportDto."""

    @abstractmethod
    def update_content(self, report_id: int, html_content: str, updated_by: str) -> object:
        """Replace HTML content. Guards finalized state. Returns ReportDto."""

    @abstractmethod
    def submit_for_review(self, report_id: int, submitted_by: str) -> object:
        """Transition report to IN_REVIEW."""

    @abstractmethod
    def mark_peer_reviewed(self, report_id: int, reviewed_by: str, comments: str) -> object:
        """Transition to PEER_REVIEWED."""

    @abstractmethod
    def finalize(self, report_id: int, finalized_by: str) -> object:
        """
        Finalize the report — encrypts content and stamps PDF hash.
        Returns ReportDto.
        """

    @abstractmethod
    def archive_report(self, report_id: int, archived_by: str) -> None:
        """Archive a finalized report."""

    @abstractmethod
    def add_appendix(self, report_id: int, appendix: str, added_by: str) -> None:
        """Attach an appendix to the report."""

    @abstractmethod
    def remove_appendix(self, report_id: int, appendix_index: int, removed_by: str) -> None:
        """Remove an appendix by index."""

    @abstractmethod
    def export_to_docx(self, report_id: int, output_path: str) -> None:
        """Export report as a DOCX file."""

    @abstractmethod
    def export_to_pdf(self, report_id: int, output_path: str) -> None:
        """Export report as a PDF file."""

    @abstractmethod
    def get_word_count(self, report_id: int) -> int:
        """Return word count of the report body."""
