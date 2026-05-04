"""application/interfaces/i_case_repository.py - Typed case repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

from application.interfaces.i_repository import IRepository
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus


class ICaseRepository(IRepository[Case]):

    @abstractmethod
    def get_by_case_number(self, case_number: str) -> Optional[Case]:
        """Return case by business identifier."""

    @abstractmethod
    def get_by_status(self, status: CaseStatus) -> List[Case]:
        """Return cases in a specific status."""

    @abstractmethod
    def get_assigned_to(self, username: str) -> List[Case]:
        """Return cases assigned to a given user."""

    @abstractmethod
    def search(self, query: str) -> List[Case]:
        """Search cases by title/case number/metadata."""
