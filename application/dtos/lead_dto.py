"""application/dtos/lead_dto.py — InvestigativeLead DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LeadDto:
    lead_id: str
    case_number: str
    name: str
    source: Optional[str]
    description: Optional[str]
    completed: bool
    completed_at: Optional[datetime]
    completed_by: Optional[str]
    created_at: datetime
    modified_at: datetime


@dataclass
class CreateLeadDto:
    case_number: str
    name: str
    source: Optional[str] = None
    description: Optional[str] = None
    created_by: str = ""


@dataclass
class UpdateLeadDto:
    lead_id: str
    name: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    modified_by: str = ""
