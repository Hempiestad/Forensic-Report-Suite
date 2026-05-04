"""
CaseStatus — State machine for forensic case lifecycle.

Valid transitions (mirrors C# CaseStatus.cs):

    DRAFT ──────────────► UNDER_INVESTIGATION
    UNDER_INVESTIGATION ─► PENDING_REVIEW
    UNDER_INVESTIGATION ◄─ PENDING_REVIEW       (send back)
    PENDING_REVIEW ──────► UNDER_LEGAL_REVIEW
    UNDER_LEGAL_REVIEW ──► CLOSED
    UNDER_LEGAL_REVIEW ◄─ PENDING_REVIEW        (send back)
    CLOSED ──────────────► ARCHIVED
    CLOSED ──────────────► UNDER_INVESTIGATION  (reopen)
    ARCHIVED             → (terminal — no outbound transitions)
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class CaseStatus(str, Enum):
    """Lifecycle statuses for a forensic case."""

    DRAFT = "draft"
    UNDER_INVESTIGATION = "under_investigation"
    PENDING_REVIEW = "pending_review"
    UNDER_LEGAL_REVIEW = "under_legal_review"
    CLOSED = "closed"
    ARCHIVED = "archived"

    # ------------------------------------------------------------------ #
    # State-machine helpers                                                #
    # ------------------------------------------------------------------ #

    @classmethod
    def _transitions(cls) -> Dict["CaseStatus", FrozenSet["CaseStatus"]]:
        return {
            cls.DRAFT: frozenset({cls.UNDER_INVESTIGATION}),
            cls.UNDER_INVESTIGATION: frozenset({cls.PENDING_REVIEW, cls.DRAFT}),
            cls.PENDING_REVIEW: frozenset({cls.UNDER_LEGAL_REVIEW, cls.UNDER_INVESTIGATION}),
            cls.UNDER_LEGAL_REVIEW: frozenset({cls.CLOSED, cls.PENDING_REVIEW}),
            cls.CLOSED: frozenset({cls.ARCHIVED, cls.UNDER_INVESTIGATION}),
            cls.ARCHIVED: frozenset(),
        }

    def can_transition_to(self, target: "CaseStatus") -> bool:
        """Return True if a transition from *self* to *target* is valid."""
        return target in self._transitions().get(self, frozenset())

    def valid_next_statuses(self) -> FrozenSet["CaseStatus"]:
        """Return the set of statuses reachable from *self*."""
        return self._transitions().get(self, frozenset())

    @property
    def is_terminal(self) -> bool:
        """True if no outbound transitions exist (archived)."""
        return not self._transitions().get(self)

    @property
    def is_open(self) -> bool:
        """True when the case is still being worked on."""
        return self not in (CaseStatus.CLOSED, CaseStatus.ARCHIVED)

    # ------------------------------------------------------------------ #
    # Display helpers                                                       #
    # ------------------------------------------------------------------ #

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    def __str__(self) -> str:  # noqa: D105
        return self.value
