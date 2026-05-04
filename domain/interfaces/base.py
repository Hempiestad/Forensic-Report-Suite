"""
domain/interfaces/base.py — Structural protocols for auditable domain entities.

These are Python typing Protocols (structural subtyping).
Concrete entities do NOT need to explicitly inherit from them;
they merely need to satisfy the structural shape.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class IEntity(Protocol):
    """Minimal contract for any domain entity that has an identity."""

    # Every entity must expose a string key so repositories can identify it.
    @property
    def entity_id(self) -> str:
        ...


@runtime_checkable
class IAuditable(Protocol):
    """Contract for entities that track creation and modification metadata."""

    created_at: datetime
    created_by: str
    modified_at: datetime
    modified_by: Optional[str]
