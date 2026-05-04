"""application/interfaces/i_audit_repository.py - Typed audit repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List

from application.interfaces.i_repository import IRepository
from domain.entities.audit_entry import AuditEntry


class IAuditRepository(IRepository[AuditEntry]):

    @abstractmethod
    def get_for_case(self, case_number: str) -> List[AuditEntry]:
        """Return full audit chain for a case in chronological order."""

    @abstractmethod
    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        """Return most recent entries across all cases."""

    @abstractmethod
    def get_last_entry_for_case(self, case_number: str) -> AuditEntry | None:
        """Return chain tail entry for case, if any."""
