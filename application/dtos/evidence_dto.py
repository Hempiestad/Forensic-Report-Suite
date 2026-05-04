"""application/dtos/evidence_dto.py — Evidence data transfer objects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EvidenceDto:
    """Read model returned from evidence-related service methods."""

    evidence_id: str
    case_number: str
    item_number: str
    description: str
    status: str
    file_path: Optional[str]
    hash_value: Optional[str]
    hash_algorithm: str
    added_by: str
    added_at: datetime
    imaged_date: Optional[datetime]
    analyzed_date: Optional[datetime]
    completed_date: Optional[datetime]


@dataclass
class AddEvidenceDto:
    """Input model for adding a new evidence item."""

    case_number: str
    item_number: str
    description: str
    added_by: str
    file_path: Optional[str] = None
    hash_value: Optional[str] = None
    hash_algorithm: str = "SHA-256"


@dataclass
class UpdateEvidenceDto:
    """Input model for updating evidence metadata."""

    evidence_id: str
    description: Optional[str] = None
    physical_description: Optional[str] = None
    digital_make: Optional[str] = None
    digital_model: Optional[str] = None
    digital_serial_number: Optional[str] = None
    evidence_found: Optional[str] = None
