"""EvidenceStatus — Imaging and analysis lifecycle for an evidence item."""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


class EvidenceStatus(str, Enum):
    NOT_IMAGED = "not_imaged"
    IMAGING_IN_PROGRESS = "imaging_in_progress"
    IMAGED = "imaged"
    ANALYSIS_IN_PROGRESS = "analysis_in_progress"
    ANALYSIS_COMPLETE = "analysis_complete"
    COMPLETED = "completed"

    @classmethod
    def _transitions(cls) -> Dict["EvidenceStatus", FrozenSet["EvidenceStatus"]]:
        return {
            cls.NOT_IMAGED: frozenset({cls.IMAGING_IN_PROGRESS}),
            cls.IMAGING_IN_PROGRESS: frozenset({cls.IMAGED, cls.NOT_IMAGED}),
            cls.IMAGED: frozenset({cls.ANALYSIS_IN_PROGRESS}),
            cls.ANALYSIS_IN_PROGRESS: frozenset({cls.ANALYSIS_COMPLETE, cls.IMAGED}),
            cls.ANALYSIS_COMPLETE: frozenset({cls.COMPLETED, cls.ANALYSIS_IN_PROGRESS}),
            cls.COMPLETED: frozenset(),
        }

    def can_transition_to(self, target: "EvidenceStatus") -> bool:
        return target in self._transitions().get(self, frozenset())

    def valid_next_statuses(self) -> FrozenSet["EvidenceStatus"]:
        return self._transitions().get(self, frozenset())

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    def __str__(self) -> str:  # noqa: D105
        return self.value
