"""application/interfaces/i_id_generator.py - Identifier generator abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod


class IIdGenerator(ABC):

    @abstractmethod
    def new_id(self) -> str:
        """Return a unique ID string."""
