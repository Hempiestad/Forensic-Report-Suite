"""infrastructure/persistence/repositories/report_repository.py - Report repository implementation."""
from __future__ import annotations

from typing import List, Optional

from domain.enums.report_status import ReportStatus

from application.interfaces.i_report_repository import IReportRepository
from domain.entities.report import Report


class InMemoryReportRepository(IReportRepository):
    """In-memory report repository for Phase 3 testing. Will be replaced with SQLite adapter."""

    def __init__(self) -> None:
        self._reports: dict[str, Report] = {}

    def get_by_id(self, entity_id: str) -> Optional[Report]:
        return self._reports.get(entity_id)

    def get_all(self) -> List[Report]:
        return list(self._reports.values())

    def add(self, entity: Report) -> None:
        self._reports[str(entity.id)] = entity

    def update(self, entity: Report) -> None:
        self._reports[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._reports.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._reports

    def get_for_case(self, case_number: str) -> Optional[Report]:
        for report in self._reports.values():
            if report.case_number == case_number:
                return report
        return None

    def get_finalized(self, report_id: str) -> Optional[Report]:
        report = self._reports.get(report_id)
        if report and report.status == ReportStatus.FINALIZED:
            return report
        return None
