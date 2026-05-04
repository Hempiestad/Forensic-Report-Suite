"""application/interfaces/i_court_date_repository.py - Typed court-date repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List

from application.interfaces.i_repository import IRepository
from domain.entities.court_date import CourtDate


class ICourtDateRepository(IRepository[CourtDate]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> List[CourtDate]:
        """Return court dates for a case."""

    @abstractmethod
    def get_upcoming(self, days: int = 30) -> List[CourtDate]:
        """Return upcoming court dates over the next N days."""
