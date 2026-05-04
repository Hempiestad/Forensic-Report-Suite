"""domain/enums/note_status.py — Note-related enums."""
from __future__ import annotations

from enum import Enum


class NoteStatus(str, Enum):
    """Lifecycle statuses for an investigation note."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class NoteType(str, Enum):
    """Categorises the type/purpose of a note."""

    OBSERVATION = "observation"
    INVESTIGATION = "investigation"
    TIMELINE = "timeline"
    TASK = "task"
    WITNESS_STATEMENT = "witness_statement"
    EVIDENCE = "evidence"
    SUSPECT = "suspect"
    LOCATION = "location"
    COMMUNICATION = "communication"
    FOLLOW_UP = "follow_up"
    MEETING = "meeting"
    ANALYSIS = "analysis"


class NotePriority(str, Enum):
    """Priority level for task-notes and triage."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NoteVisibility(str, Enum):
    """Access-control visibility scope for a note."""

    PRIVATE = "private"
    TEAM = "team"
    CASE_LEVEL = "case_level"
    PUBLIC = "public"
