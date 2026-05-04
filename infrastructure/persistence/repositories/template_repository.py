"""infrastructure/persistence/repositories/template_repository.py - Template repository implementation."""
from __future__ import annotations

from typing import List, Optional

from application.interfaces.i_template_repository import ITemplateRepository
from domain.entities.template import Template


class InMemoryTemplateRepository(ITemplateRepository):
    """In-memory template repository for Phase 3 testing. Will be replaced with SQLite adapter."""

    def __init__(self) -> None:
        self._templates: dict[str, Template] = {}

    def get_by_id(self, entity_id: str) -> Optional[Template]:
        return self._templates.get(entity_id)

    def get_all(self) -> List[Template]:
        return list(self._templates.values())

    def add(self, entity: Template) -> None:
        self._templates[str(entity.id)] = entity

    def update(self, entity: Template) -> None:
        self._templates[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._templates.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._templates

    def get_by_name(self, name: str) -> Optional[Template]:
        for t in self._templates.values():
            if t.name == name:
                return t
        return None

    def get_published(self) -> List[Template]:
        return [t for t in self._templates.values() if t.is_published]

    def get_by_category(self, category: str) -> List[Template]:
        return [t for t in self._templates.values() if str(t.category) == category]

    def search(self, query: str) -> List[Template]:
        q = query.lower()
        return [t for t in self._templates.values() if q in t.name.lower() or (t.description and q in t.description.lower())]
