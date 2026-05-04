"""application/dtos/court_date_dto.py - Court date DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CourtDateDto:
    court_date_id: str
    case_number: str
    hearing_type: str
    court_date: datetime
    location: str
    notes: str
    created_by: str
    created_at: datetime


@dataclass
class CreateCourtDateDto:
    case_number: str
    hearing_type: str
    court_date: datetime
    created_by: str
    location: str = ""
    notes: str = ""


@dataclass
class UpdateCourtDateDto:
    court_date_id: str
    hearing_type: Optional[str] = None
    court_date: Optional[datetime] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    updated_by: str = ""
