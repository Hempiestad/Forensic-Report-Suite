"""application/dtos/case_dto.py — Case data transfer objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CaseDto:
    """Read model returned from ICaseService."""

    case_number: str
    title: str
    assigned_to: str
    created_by: str
    status: str
    examiner_id: Optional[str]
    review_comments: str
    trial_date: Optional[datetime]
    sentencing_date: Optional[datetime]
    created_at: datetime
    modified_at: Optional[datetime]
    modified_by: Optional[str]
    evidence_count: int = 0
    open_legal_process_count: int = 0
    overdue_legal_count: int = 0
    peer_reviewers: List[str] = field(default_factory=list)


@dataclass
class CreateCaseDto:
    """Input model for creating a new case."""

    case_number: str
    title: str
    assigned_to: str
    created_by: str
    examiner_id: Optional[str] = None
    trial_date: Optional[datetime] = None
    sentencing_date: Optional[datetime] = None


@dataclass
class UpdateCaseDto:
    """Input model for updating an existing case."""

    case_number: str
    title: Optional[str] = None
    assigned_to: Optional[str] = None
    examiner_id: Optional[str] = None
    review_comments: Optional[str] = None
    trial_date: Optional[datetime] = None
    sentencing_date: Optional[datetime] = None
    modified_by: str = ""
