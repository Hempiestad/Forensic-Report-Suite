"""application/interfaces/i_lead_repository.py — InvestigativeLead repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List

from application.interfaces.i_repository import IRepository
from domain.entities.investigative_lead import InvestigativeLead


class IInvestigativeLeadRepository(IRepository[InvestigativeLead]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> List[InvestigativeLead]:
        """Return all leads for a given case."""

    @abstractmethod
    def get_open_for_case(self, case_number: str) -> List[InvestigativeLead]:
        """Return only incomplete leads for a given case."""
