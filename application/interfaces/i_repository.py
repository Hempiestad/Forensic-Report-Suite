"""
application/interfaces/i_repository.py — Generic repository ABC.

Concrete implementations live in infrastructure/persistence/repositories/.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Base contract for all entity repositories."""

    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Return entity by its primary identifier, or None if not found."""

    @abstractmethod
    def get_all(self) -> List[T]:
        """Return all entities of this type."""

    @abstractmethod
    def add(self, entity: T) -> None:
        """Persist a new entity."""

    @abstractmethod
    def update(self, entity: T) -> None:
        """Persist changes to an existing entity."""

    @abstractmethod
    def delete(self, entity_id: str) -> None:
        """Remove entity by identifier."""

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Return True if entity with the given identifier exists."""
