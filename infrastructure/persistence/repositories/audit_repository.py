"""infrastructure/persistence/repositories/audit_repository.py - Audit entry repository implementation."""
from __future__ import annotations

from typing import List, Optional

from application.interfaces.i_audit_repository import IAuditRepository
from domain.entities.audit_entry import AuditEntry


class InMemoryAuditRepository(IAuditRepository):
    """In-memory audit repository for Phase 3 testing. Will be replaced with SQLite adapter."""

    def __init__(self) -> None:
        self._entries: dict[str, AuditEntry] = {}
        self._next_id = 1

    def get_by_id(self, entity_id: str) -> Optional[AuditEntry]:
        return self._entries.get(entity_id)

    def get_all(self) -> List[AuditEntry]:
        return list(self._entries.values())

    def add(self, entity: AuditEntry) -> None:
        # Auto-assign ID if not set
        if not entity.id:
            entity.id = self._next_id
            self._next_id += 1
        self._entries[str(entity.id)] = entity

    def update(self, entity: AuditEntry) -> None:
        self._entries[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._entries.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._entries

    def get_for_case(self, case_number: str) -> List[AuditEntry]:
        return [e for e in self._entries.values() if e.case_number == case_number]

    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        entries = sorted(self._entries.values(), key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_last_entry_for_case(self, case_number: str) -> Optional[AuditEntry]:
        case_entries = self.get_for_case(case_number)
        if case_entries:
            return max(case_entries, key=lambda e: e.timestamp)
        return None
