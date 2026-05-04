"""application/interfaces/i_lead_service.py — InvestigativeLead service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IInvestigativeLeadService(ABC):

    @abstractmethod
    def create_lead(self, dto) -> object:
        """Create a new investigative lead. Returns LeadDto."""

    @abstractmethod
    def update_lead(self, dto) -> object:
        """Update lead fields. Returns LeadDto."""

    @abstractmethod
    def complete_lead(self, lead_id: str, completed_by: str) -> object:
        """Mark a lead as completed. Returns LeadDto."""

    @abstractmethod
    def reopen_lead(self, lead_id: str, reopened_by: str) -> object:
        """Reopen a completed lead. Returns LeadDto."""

    @abstractmethod
    def delete_lead(self, lead_id: str, deleted_by: str) -> None:
        """Remove a lead."""

    @abstractmethod
    def get_lead(self, lead_id: str) -> Optional[object]:
        """Return LeadDto or None."""

    @abstractmethod
    def get_leads_for_case(self, case_number: str) -> List[object]:
        """Return all leads for a case."""

    @abstractmethod
    def get_open_leads_for_case(self, case_number: str) -> List[object]:
        """Return open (incomplete) leads for a case."""
