"""application/interfaces/i_clock.py - Time provider abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class IClock(ABC):

    @abstractmethod
    def utcnow(self) -> datetime:
        """Return current UTC timestamp."""

    @abstractmethod
    def now_local(self) -> datetime:
        """Return current local timestamp."""
