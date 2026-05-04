"""application/interfaces/i_evidence_service.py - Evidence service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IEvidenceService(ABC):

    @abstractmethod
    def get_evidence(self, evidence_id: str) -> Optional[object]:
        """Return EvidenceDto or None."""

    @abstractmethod
    def get_evidence_for_case(self, case_number: str) -> List[object]:
        """Return evidence list for a case."""

    @abstractmethod
    def add_evidence(self, dto) -> object:
        """Add evidence item. Accepts AddEvidenceDto and returns EvidenceDto."""

    @abstractmethod
    def update_evidence(self, evidence_id: str, dto, updated_by: str) -> object:
        """Update evidence metadata and return EvidenceDto."""

    @abstractmethod
    def remove_evidence(self, evidence_id: str, removed_by: str) -> None:
        """Remove evidence item."""

    @abstractmethod
    def start_imaging(self, evidence_id: str, changed_by: str) -> object:
        """Transition evidence status to imaging in progress."""

    @abstractmethod
    def mark_imaged(self, evidence_id: str, changed_by: str) -> object:
        """Transition evidence status to imaged."""

    @abstractmethod
    def start_analysis(self, evidence_id: str, changed_by: str) -> object:
        """Transition evidence status to analysis in progress."""

    @abstractmethod
    def complete_analysis(self, evidence_id: str, changed_by: str) -> object:
        """Transition evidence status to analysis complete."""

    @abstractmethod
    def mark_completed(self, evidence_id: str, changed_by: str) -> object:
        """Transition evidence status to completed."""

    @abstractmethod
    def get_digital_evidence_for_case(self, case_number: str) -> List[object]:
        """Return digital evidence items for a case (item_type == 'Digital')."""

    @abstractmethod
    def get_incomplete_evidence_for_case(self, case_number: str) -> List[object]:
        """Return evidence items that have not yet reached 'completed' status."""
