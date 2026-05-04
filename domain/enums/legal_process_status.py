"""domain/enums/legal_process_status.py — LegalProcess state-machine enum."""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class LegalProcessStatus(str, Enum):
    """Lifecycle statuses for a legal process (subpoena, warrant, court order, etc.)."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    UNDER_ANALYSIS = "under_analysis"
    COMPLETED = "completed"
    NO_DATA = "no_data"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"

    # ------------------------------------------------------------------ #
    # State-machine helpers                                                #
    # ------------------------------------------------------------------ #

    @classmethod
    def _transitions(cls) -> Dict["LegalProcessStatus", FrozenSet["LegalProcessStatus"]]:
        return {
            cls.PENDING: frozenset({cls.SUBMITTED, cls.CANCELLED}),
            cls.SUBMITTED: frozenset({cls.RECEIVED, cls.EXPIRED, cls.CANCELLED}),
            cls.RECEIVED: frozenset({cls.UNDER_ANALYSIS, cls.NO_DATA, cls.CANCELLED}),
            cls.UNDER_ANALYSIS: frozenset({cls.COMPLETED, cls.NO_DATA, cls.CANCELLED}),
            cls.COMPLETED: frozenset({cls.ARCHIVED}),
            cls.NO_DATA: frozenset({cls.ARCHIVED}),
            cls.EXPIRED: frozenset({cls.PENDING}),           # can re-submit after expiry
            cls.CANCELLED: frozenset(),
            cls.ARCHIVED: frozenset(),
        }

    def can_transition_to(self, target: "LegalProcessStatus") -> bool:
        """Return True if transitioning from *self* to *target* is valid."""
        return target in self._transitions().get(self, frozenset())

    @property
    def is_terminal(self) -> bool:
        """Return True if no further transitions are permitted."""
        return not bool(self._transitions().get(self))

    @property
    def is_active(self) -> bool:
        """Return True if the process is still in-flight."""
        return self not in (
            self.COMPLETED,
            self.NO_DATA,
            self.EXPIRED,
            self.CANCELLED,
            self.ARCHIVED,
        )
