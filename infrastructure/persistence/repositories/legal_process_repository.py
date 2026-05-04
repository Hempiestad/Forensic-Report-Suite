"""infrastructure/persistence/repositories/legal_process_repository.py - Legal process repository implementation."""
from __future__ import annotations

from typing import List, Optional

from application.interfaces.i_legal_process_repository import ILegalProcessRepository
from domain.entities.legal_process import LegalProcess


class InMemoryLegalProcessRepository(ILegalProcessRepository):
    """In-memory legal process repository for Phase 3 testing. Will be replaced with SQLite adapter.
    
    Note: Legal processes are children of Case aggregates and are typically accessed through
    CaseRepository. This repository exists for direct access queries.
    """

    def __init__(self) -> None:
        self._processes: dict[str, LegalProcess] = {}

    def get_by_id(self, entity_id: str) -> Optional[LegalProcess]:
        return self._processes.get(entity_id)

    def get_all(self) -> List[LegalProcess]:
        return list(self._processes.values())

    def add(self, entity: LegalProcess) -> None:
        self._processes[str(entity.id)] = entity

    def update(self, entity: LegalProcess) -> None:
        self._processes[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._processes.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._processes

    def get_for_case(self, case_number: str) -> List[LegalProcess]:
        return [p for p in self._processes.values() if p.case_number == case_number]

    def get_overdue(self) -> List[LegalProcess]:
        return [p for p in self._processes.values() if p.is_overdue]

    def get_due_soon(self, days: int = 7) -> List[LegalProcess]:
        """Get processes due within specified days."""
        return [p for p in self._processes.values() if p.days_until_due <= days and p.days_until_due >= 0]
