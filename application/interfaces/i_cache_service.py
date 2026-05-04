"""application/interfaces/i_cache_service.py - Cache abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class ICacheService(ABC):

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value by cache key."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value with optional TTL."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete one cache key."""

    @abstractmethod
    def clear(self, namespace: Optional[str] = None) -> None:
        """Clear cache globally or by namespace."""
