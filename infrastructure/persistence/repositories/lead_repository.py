"""infrastructure/persistence/repositories/lead_repository.py — In-memory lead repository."""
from __future__ import annotations

from typing import Dict, List, Optional

from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
from domain.entities.investigative_lead import InvestigativeLead


class InMemoryInvestigativeLeadRepository(IInvestigativeLeadRepository):
    """Dict-backed in-memory repository for testing and memory provider."""

    def __init__(self) -> None:
        self._store: Dict[str, InvestigativeLead] = {}

    def get_by_id(self, entity_id: str) -> Optional[InvestigativeLead]:
        return self._store.get(str(entity_id))

    def get_all(self) -> List[InvestigativeLead]:
        return list(self._store.values())

    def add(self, entity: InvestigativeLead) -> None:
        self._store[str(entity.id)] = entity

    def update(self, entity: InvestigativeLead) -> None:
        self._store[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._store.pop(str(entity_id), None)

    def exists(self, entity_id: str) -> bool:
        return str(entity_id) in self._store

    def get_for_case(self, case_number: str) -> List[InvestigativeLead]:
        return [l for l in self._store.values() if l.case_number == case_number]

    def get_open_for_case(self, case_number: str) -> List[InvestigativeLead]:
        return [
            l for l in self._store.values()
            if l.case_number == case_number and not l.completed
        ]
