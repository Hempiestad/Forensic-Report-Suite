"""application/dtos/legal_workflow_dto.py - Legal workflow DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LegalProcessDto:
    process_id: str
    case_number: str
    process_type: str
    status: str
    created_at: datetime
    created_by: str
    due_date: Optional[datetime]
    investigator_approved_by: Optional[str]
    investigator_approved_at: Optional[datetime]
    state_attorney_approved_by: Optional[str]
    state_attorney_approved_at: Optional[datetime]
    judicial_approved_by: Optional[str]
    judicial_approved_at: Optional[datetime]
    sent_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass
class CreateLegalProcessDto:
    case_number: str
    process_type: str
    created_by: str
    due_date: Optional[datetime] = None


@dataclass
class UpdateLegalProcessDto:
    process_id: str
    process_type: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    updated_by: str = ""
