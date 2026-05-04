from __future__ import annotations

from typing import Dict, List, Optional

from application.interfaces.i_audit_repository import IAuditRepository
from application.services.audit_service import AuditService
from domain.entities.audit_entry import AuditEntry


class InMemoryAuditRepository(IAuditRepository):
    def __init__(self) -> None:
        self._items: List[AuditEntry] = []
        self._next_id = 1

    def get_by_id(self, entity_id: str) -> Optional[AuditEntry]:
        for item in self._items:
            if str(item.id) == entity_id:
                return item
        return None

    def get_all(self) -> List[AuditEntry]:
        return list(self._items)

    def add(self, entity: AuditEntry) -> None:
        entity.id = self._next_id
        self._next_id += 1
        self._items.append(entity)

    def update(self, entity: AuditEntry) -> None:
        for idx, item in enumerate(self._items):
            if item.id == entity.id:
                self._items[idx] = entity
                return

    def delete(self, entity_id: str) -> None:
        self._items = [i for i in self._items if str(i.id) != entity_id]

    def exists(self, entity_id: str) -> bool:
        return any(str(i.id) == entity_id for i in self._items)

    def get_for_case(self, case_number: str) -> List[AuditEntry]:
        return [i for i in self._items if i.case_number == case_number]

    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        return list(reversed(self._items))[:limit]

    def get_last_entry_for_case(self, case_number: str) -> AuditEntry | None:
        entries = self.get_for_case(case_number)
        if not entries:
            return None
        return entries[-1]


def test_log_builds_hash_chain() -> None:
    repo = InMemoryAuditRepository()
    service = AuditService(repo)

    service.log("CASE-001", "CASE_CREATED", "admin", {"title": "First"})
    service.log("CASE-001", "CASE_UPDATED", "admin", {"field": "title"})

    entries = repo.get_for_case("CASE-001")
    assert len(entries) == 2
    assert entries[0].previous_hash == "0" * 64
    assert entries[1].previous_hash == entries[0].entry_hash


def test_verify_chain_integrity_detects_tampering() -> None:
    repo = InMemoryAuditRepository()
    service = AuditService(repo)

    service.log("CASE-010", "CASE_CREATED", "admin", {"ok": True})
    service.log("CASE-010", "CASE_UPDATED", "admin", {"ok": True})
    assert service.verify_chain_integrity("CASE-010") is True

    # Tamper with first entry payload after hash generation.
    repo.get_for_case("CASE-010")[0].details["ok"] = False
    assert service.verify_chain_integrity("CASE-010") is False
