"""application/interfaces/i_report_repository.py - Typed report repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import Optional

from application.interfaces.i_repository import IRepository
from domain.entities.report import Report


class IReportRepository(IRepository[Report]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> Optional[Report]:
        """Return report for case if present."""

    @abstractmethod
    def get_finalized(self, report_id: str) -> Optional[Report]:
        """Return finalized report by identifier."""
