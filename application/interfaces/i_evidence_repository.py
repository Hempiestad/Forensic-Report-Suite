"""application/interfaces/i_evidence_repository.py — Evidence repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

from application.interfaces.i_repository import IRepository
from domain.entities.evidence import Evidence
from domain.enums.evidence_status import EvidenceStatus


class IEvidenceRepository(IRepository[Evidence]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> List[Evidence]:
        """Return all evidence items for a case."""

    @abstractmethod
    def get_by_item_number(self, case_number: str, item_number: str) -> Optional[Evidence]:
        """Return evidence by case + item number."""

    @abstractmethod
    def get_by_status(self, status: EvidenceStatus) -> List[Evidence]:
        """Return evidence filtered by status."""
