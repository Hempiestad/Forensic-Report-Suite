"""application/interfaces/i_legal_process_repository.py - Typed legal-process repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List

from application.interfaces.i_repository import IRepository
from domain.entities.legal_process import LegalProcess


class ILegalProcessRepository(IRepository[LegalProcess]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> List[LegalProcess]:
        """Return legal processes for a case."""

    @abstractmethod
    def get_overdue(self) -> List[LegalProcess]:
        """Return processes currently overdue."""

    @abstractmethod
    def get_due_soon(self, days: int = 7) -> List[LegalProcess]:
        """Return processes due within N days."""
