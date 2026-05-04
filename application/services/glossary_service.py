"""application/services/glossary_service.py — GlossaryService (Phase 6)."""
from __future__ import annotations

from typing import Dict, List, Optional

from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_glossary_service import IGlossaryService
from application.interfaces.i_report_repository import IReportRepository
from domain.exceptions.domain_exceptions import DomainValidationError

# Import the built-in forensic glossary
try:
    from glossary import GLOSSARY as _DEFAULT_GLOSSARY
except ImportError:  # running in environments without root on sys.path
    _DEFAULT_GLOSSARY: Dict[str, str] = {}


class GlossaryService(IGlossaryService):
    """Application service providing forensic glossary assistance."""

    def __init__(
        self,
        report_repository: IReportRepository,
        audit_service: IAuditService,
        glossary_dict: Optional[Dict[str, str]] = None,
    ) -> None:
        self._reports = report_repository
        self._audit = audit_service
        self._glossary: Dict[str, str] = glossary_dict if glossary_dict is not None else _DEFAULT_GLOSSARY
        # Per-report footnote tracking: {report_id: {term: footnote_number}}
        self._footnotes: Dict[int, Dict[str, int]] = {}

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get_all_terms(self) -> List[dict]:
        return [{"term": k, "definition": v} for k, v in sorted(self._glossary.items())]

    def find_matches(self, text: str) -> List[dict]:
        if not text:
            return []
        lower = text.lower()
        return [
            {"term": term, "definition": defn}
            for term, defn in self._glossary.items()
            if term.lower() in lower
        ]

    def suggest_term(self, partial: str, limit: int = 10) -> List[dict]:
        if not partial:
            return []
        lower = partial.lower()
        results = [
            {"term": term, "definition": defn}
            for term, defn in self._glossary.items()
            if lower in term.lower()
        ]
        return results[:limit]

    def get_existing_footnote(self, report_id: int, term: str) -> Optional[int]:
        return self._footnotes.get(report_id, {}).get(term)

    # ------------------------------------------------------------------ #
    # Mutations                                                            #
    # ------------------------------------------------------------------ #

    def add_footnote(self, report_id: int, term: str, added_by: str) -> int:
        if term not in self._glossary:
            raise DomainValidationError("term", f"Term '{term}' not found in glossary.")
        existing = self.get_existing_footnote(report_id, term)
        if existing is not None:
            return existing
        report = self._reports.get_by_id(str(report_id))
        if report is None:
            raise DomainValidationError("report_id", f"Report '{report_id}' not found.")
        # Next footnote number for this report
        report_footnotes = self._footnotes.setdefault(report_id, {})
        footnote_number = len(report_footnotes) + 1
        report_footnotes[term] = footnote_number
        # Append footnote text to report
        definition = self._glossary[term]
        footnote_block = f"\n<p id='fn{footnote_number}'>[{footnote_number}] <b>{term}</b>: {definition}</p>"
        report.report_html = (report.report_html or "") + footnote_block
        self._reports.update(report)
        self._audit.log_event(
            event_type="GLOSSARY_FOOTNOTE_ADDED",
            description=f"Glossary footnote [{footnote_number}] added for term '{term}' in report {report_id}",
            actor=added_by,
            entity_id=str(report_id),
            metadata={"term": term, "footnote_number": footnote_number},
        )
        return footnote_number
