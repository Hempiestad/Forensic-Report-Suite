"""infrastructure/persistence/repositories/evidence_repository.py — In-memory Evidence repository."""
from __future__ import annotations

from typing import Dict, List, Optional

from application.interfaces.i_evidence_repository import IEvidenceRepository
from domain.entities.evidence import Evidence
from domain.enums.evidence_status import EvidenceStatus


class InMemoryEvidenceRepository(IEvidenceRepository):
    """In-memory Evidence repository (testing / memory provider)."""

    def __init__(self) -> None:
        self._store: Dict[str, Evidence] = {}

    def get_by_id(self, entity_id: str) -> Optional[Evidence]:
        return self._store.get(str(entity_id))

    def get_all(self) -> List[Evidence]:
        return list(self._store.values())

    def add(self, entity: Evidence) -> None:
        self._store[str(entity.id)] = entity

    def update(self, entity: Evidence) -> None:
        self._store[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._store.pop(str(entity_id), None)

    def exists(self, entity_id: str) -> bool:
        return str(entity_id) in self._store

    def get_for_case(self, case_number: str) -> List[Evidence]:
        return [e for e in self._store.values() if e.case_number == case_number]

    def get_by_item_number(self, case_number: str, item_number: str) -> Optional[Evidence]:
        for e in self._store.values():
            if e.case_number == case_number and e.evidence_item_number == item_number:
                return e
        return None

    def get_by_status(self, status: EvidenceStatus) -> List[Evidence]:
        return [e for e in self._store.values() if e.status == status]
