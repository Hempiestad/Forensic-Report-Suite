"""application/interfaces/i_glossary_service.py - Glossary assistance contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IGlossaryService(ABC):

    @abstractmethod
    def get_all_terms(self) -> List[dict]:
        """Return all glossary terms and definitions."""

    @abstractmethod
    def find_matches(self, text: str) -> List[dict]:
        """Find glossary term matches in text."""

    @abstractmethod
    def suggest_term(self, partial: str, limit: int = 10) -> List[dict]:
        """Return auto-complete suggestions for partial term text."""

    @abstractmethod
    def add_footnote(self, report_id: int, term: str, added_by: str) -> int:
        """Add glossary footnote to report and return footnote number."""

    @abstractmethod
    def get_existing_footnote(self, report_id: int, term: str) -> Optional[int]:
        """Return existing footnote number for term if already present."""
