"""ReportStatus — Lifecycle for a forensic report document."""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class ReportStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PEER_REVIEWED = "peer_reviewed"
    FINALIZED = "finalized"
    ARCHIVED = "archived"

    @classmethod
    def _transitions(cls) -> Dict["ReportStatus", FrozenSet["ReportStatus"]]:
        return {
            cls.DRAFT: frozenset({cls.IN_REVIEW}),
            cls.IN_REVIEW: frozenset({cls.PEER_REVIEWED, cls.DRAFT}),
            cls.PEER_REVIEWED: frozenset({cls.FINALIZED, cls.IN_REVIEW}),
            cls.FINALIZED: frozenset({cls.ARCHIVED}),
            cls.ARCHIVED: frozenset(),
        }

    def can_transition_to(self, target: "ReportStatus") -> bool:
        return target in self._transitions().get(self, frozenset())

    def valid_next_statuses(self) -> FrozenSet["ReportStatus"]:
        return self._transitions().get(self, frozenset())

    @property
    def is_editable(self) -> bool:
        return self in (ReportStatus.DRAFT, ReportStatus.IN_REVIEW)

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    def __str__(self) -> str:  # noqa: D105
        return self.value
