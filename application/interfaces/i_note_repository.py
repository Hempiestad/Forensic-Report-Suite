"""application/interfaces/i_note_repository.py — Note repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

from application.interfaces.i_repository import IRepository
from domain.entities.note import Note


class INoteRepository(IRepository[Note]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> List[Note]:
        """Return all active notes for a case."""

    @abstractmethod
    def search(self, query: str, case_number: Optional[str] = None) -> List[Note]:
        """Full-text search across title/body, optionally scoped to one case."""

    @abstractmethod
    def get_archived(self, case_number: str) -> List[Note]:
        """Return archived notes for a case."""

    @abstractmethod
    def get_pending_approval(self, case_number: str) -> List[Note]:
        """Return notes in pending_approval status for a case."""

    @abstractmethod
    def get_by_tag(self, case_number: str, tag: str) -> List[Note]:
        """Return notes that carry the given tag for a case."""

    @abstractmethod
    def get_by_type(self, case_number: str, note_type: str) -> List[Note]:
        """Return notes of a specific type for a case."""

    @abstractmethod
    def get_available_tags(self, case_number: str) -> List[str]:
        """Return sorted unique tag values used across all notes for a case."""

