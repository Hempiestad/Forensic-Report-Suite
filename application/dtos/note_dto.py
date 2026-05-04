"""application/dtos/note_dto.py - Note DTOs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class NoteDto:
    note_id: str
    case_number: str
    title: str
    body: str
    created_by: str
    created_at: datetime
    modified_at: Optional[datetime]
    modified_by: Optional[str]
    # Extended fields
    status: str = "active"
    tags: List[str] = field(default_factory=list)
    note_type: Optional[str] = None
    priority: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comments: Optional[str] = None


@dataclass
class CreateNoteDto:
    case_number: str
    title: str
    body: str
    created_by: str
    note_type: Optional[str] = None
    priority: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class UpdateNoteDto:
    note_id: str
    title: Optional[str] = None
    body: Optional[str] = None
    modified_by: str = ""
    note_type: Optional[str] = None
    priority: Optional[str] = None


@dataclass
class ArchiveNoteDto:
    note_id: str
    archived_by: str


@dataclass
class RestoreNoteDto:
    note_id: str
    restored_by: str


@dataclass
class SubmitNoteForApprovalDto:
    note_id: str
    submitted_by: str


@dataclass
class ApproveNoteDto:
    note_id: str
    approved_by: str
    comments: Optional[str] = None


@dataclass
class RejectNoteDto:
    note_id: str
    rejected_by: str
    reason: str


@dataclass
class AddTagDto:
    note_id: str
    tag_name: str
    added_by: str


@dataclass
class RemoveTagDto:
    note_id: str
    tag_name: str
    removed_by: str


@dataclass
class NoteStatisticsDto:
    case_number: str
    total: int
    active: int
    archived: int
    pending_approval: int
    approved: int
    rejected: int
    by_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    all_tags: List[str] = field(default_factory=list)

