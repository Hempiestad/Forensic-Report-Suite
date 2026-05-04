"""infrastructure/persistence/repositories/case_repository.py - Case repository implementation."""
from __future__ import annotations

from typing import List, Optional

from application.interfaces.i_case_repository import ICaseRepository
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus


class InMemoryCaseRepository(ICaseRepository):
    """In-memory case repository for Phase 3 testing. Will be replaced with SQLite adapter in Phase 3."""

    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}

    def get_by_id(self, entity_id: str) -> Optional[Case]:
        return self._cases.get(entity_id)

    def get_all(self) -> List[Case]:
        return list(self._cases.values())

    def add(self, entity: Case) -> None:
        self._cases[entity.case_number] = entity

    def update(self, entity: Case) -> None:
        self._cases[entity.case_number] = entity

    def delete(self, entity_id: str) -> None:
        self._cases.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._cases

    def get_by_case_number(self, case_number: str) -> Optional[Case]:
        return self._cases.get(case_number)

    def get_by_status(self, status: CaseStatus) -> List[Case]:
        return [c for c in self._cases.values() if c.status == status]

    def get_assigned_to(self, username: str) -> List[Case]:
        return [c for c in self._cases.values() if c.assigned_to == username]

    def search(self, query: str) -> List[Case]:
        q = query.lower()
        return [c for c in self._cases.values() if q in c.case_number.lower() or q in c.title.lower()]
