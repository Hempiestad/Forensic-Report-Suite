"""domain/entities/report.py — Forensic report document entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.enums.report_status import ReportStatus
from domain.exceptions.domain_exceptions import (
    DomainValidationError,
    InvalidStatusTransitionError,
    ReportFinalizedError,
)


@dataclass
class Report:
    """Represents a forensic examination report attached to a case."""

    # ── Identity ─────────────────────────────────────────────────────────
    id: int
    case_number: str

    # ── Content (stored encrypted in DB) ─────────────────────────────────
    report_html: Optional[str] = None          # Decrypted HTML for editing
    report_html_encrypted: Optional[bytes] = None  # BLOB as stored in DB

    # ── Status ───────────────────────────────────────────────────────────
    status: ReportStatus = field(default=ReportStatus.DRAFT)

    # ── Appendices ───────────────────────────────────────────────────────
    _appendices: List[str] = field(default_factory=list, repr=False, compare=False)

    # ── Finalisation ─────────────────────────────────────────────────────
    final_pdf_hash: Optional[str] = None
    finalized_by: Optional[str] = None
    finalized_at: Optional[datetime] = None

    # ── Audit ────────────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    modified_at: datetime = field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(cls, id: int, case_number: str, created_by: str) -> "Report":
        if not case_number:
            raise DomainValidationError("case_number", "Case number is required.")
        return cls(id=id, case_number=case_number, created_by=created_by)

    # ================================================================== #
    # Status transitions                                                   #
    # ================================================================== #

    def transition_to(self, new_status: ReportStatus, changed_by: str) -> None:
        if not self.status.can_transition_to(new_status):
            raise InvalidStatusTransitionError(
                str(self.id), str(self.status), str(new_status)
            )
        self.status = new_status
        self._touch(changed_by)

    def submit_for_review(self, changed_by: str) -> None:
        self.transition_to(ReportStatus.IN_REVIEW, changed_by)

    def mark_peer_reviewed(self, changed_by: str) -> None:
        self.transition_to(ReportStatus.PEER_REVIEWED, changed_by)

    def finalize(self, changed_by: str, pdf_hash: Optional[str] = None) -> None:
        self.transition_to(ReportStatus.FINALIZED, changed_by)
        self.finalized_by = changed_by
        self.finalized_at = datetime.utcnow()
        if pdf_hash:
            self.final_pdf_hash = pdf_hash

    # ================================================================== #
    # Content editing                                                      #
    # ================================================================== #

    def update_content(self, html: str, changed_by: str) -> None:
        if not self.status.is_editable:
            raise ReportFinalizedError(self.id)
        self.report_html = html
        self._touch(changed_by)

    # ================================================================== #
    # Appendices                                                           #
    # ================================================================== #

    @property
    def appendices(self) -> List[str]:
        return list(self._appendices)

    def add_appendix(self, file_path: str, changed_by: str) -> None:
        if not self.status.is_editable:
            raise ReportFinalizedError(self.id)
        if not file_path or not file_path.strip():
            raise DomainValidationError("file_path", "Appendix path cannot be empty.")
        if file_path not in self._appendices:
            self._appendices.append(file_path)
            self._touch(changed_by)

    def remove_appendix(self, file_path: str, changed_by: str) -> None:
        if not self.status.is_editable:
            raise ReportFinalizedError(self.id)
        if file_path in self._appendices:
            self._appendices.remove(file_path)
            self._touch(changed_by)

    # ================================================================== #
    # Properties                                                           #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return str(self.id)

    @property
    def is_finalized(self) -> bool:
        return self.status in (ReportStatus.FINALIZED, ReportStatus.ARCHIVED)

    @property
    def word_count(self) -> int:
        if not self.report_html:
            return 0
        import re
        text = re.sub(r"<[^>]+>", " ", self.report_html)
        return len(text.split())

    # ================================================================== #
    # Helpers                                                              #
    # ================================================================== #

    def _touch(self, changed_by: Optional[str] = None) -> None:
        self.modified_at = datetime.utcnow()
        if changed_by:
            self.modified_by = changed_by

    def __repr__(self) -> str:
        return f"Report(id={self.id}, case={self.case_number!r}, status={self.status!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Report):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
