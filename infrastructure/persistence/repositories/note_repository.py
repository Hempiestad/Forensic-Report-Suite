"""infrastructure/persistence/repositories/note_repository.py — In-memory Note repository."""
from __future__ import annotations

from typing import Dict, List, Optional

from application.interfaces.i_note_repository import INoteRepository
from domain.entities.note import Note
from domain.enums.note_status import NoteStatus


class InMemoryNoteRepository(INoteRepository):
    """In-memory Note repository (testing / memory provider)."""

    def __init__(self) -> None:
        self._store: Dict[str, Note] = {}

    def get_by_id(self, entity_id: str) -> Optional[Note]:
        return self._store.get(str(entity_id))

    def get_all(self) -> List[Note]:
        return list(self._store.values())

    def add(self, entity: Note) -> None:
        self._store[str(entity.id)] = entity

    def update(self, entity: Note) -> None:
        self._store[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._store.pop(str(entity_id), None)

    def exists(self, entity_id: str) -> bool:
        return str(entity_id) in self._store

    def get_for_case(self, case_number: str) -> List[Note]:
        return [
            n for n in self._store.values()
            if n.case_number == case_number
            and n.status == NoteStatus.ACTIVE
        ]

    def search(self, query: str, case_number: Optional[str] = None) -> List[Note]:
        q = query.lower()
        results = [
            n for n in self._store.values()
            if q in n.title.lower() or q in n.body.lower()
        ]
        if case_number is not None:
            results = [n for n in results if n.case_number == case_number]
        return results

    def get_archived(self, case_number: str) -> List[Note]:
        return [
            n for n in self._store.values()
            if n.case_number == case_number and n.status == NoteStatus.ARCHIVED
        ]

    def get_pending_approval(self, case_number: str) -> List[Note]:
        return [
            n for n in self._store.values()
            if n.case_number == case_number and n.status == NoteStatus.PENDING_APPROVAL
        ]

    def get_by_tag(self, case_number: str, tag: str) -> List[Note]:
        tag_lower = tag.strip().lower()
        return [
            n for n in self._store.values()
            if n.case_number == case_number
            and any(t.lower() == tag_lower for t in n.tags)
        ]

    def get_by_type(self, case_number: str, note_type: str) -> List[Note]:
        return [
            n for n in self._store.values()
            if n.case_number == case_number and n.note_type == note_type
        ]

    def get_available_tags(self, case_number: str) -> List[str]:
        tags: set = set()
        for n in self._store.values():
            if n.case_number == case_number:
                tags.update(n.tags)
        return sorted(tags)

