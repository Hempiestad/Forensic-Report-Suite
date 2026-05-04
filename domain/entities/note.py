"""domain/entities/note.py — Investigation note attached to a case."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.enums.note_status import NoteStatus
from domain.exceptions.domain_exceptions import DomainValidationError, InvalidStatusTransitionError


@dataclass
class Note:
    """An investigation note associated with a case."""

    # ── Identity ─────────────────────────────────────────────────────────
    id: str
    case_number: str

    # ── Content ──────────────────────────────────────────────────────────
    title: str
    body: str

    # ── Classification ───────────────────────────────────────────────────
    status: NoteStatus = field(default=NoteStatus.ACTIVE)
    note_type: Optional[str] = None          # e.g. "observation", "task", "timeline"
    priority: Optional[str] = None           # e.g. "low", "medium", "high"
    tags: List[str] = field(default_factory=list)

    # ── Approval ─────────────────────────────────────────────────────────
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comments: Optional[str] = None

    # ── Audit ────────────────────────────────────────────────────────────
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: Optional[datetime] = None
    modified_by: Optional[str] = None

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(
        cls,
        id: str,
        case_number: str,
        title: str,
        body: str,
        created_by: str,
        note_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> "Note":
        if not case_number or not case_number.strip():
            raise DomainValidationError("case_number", "Case number is required.")
        if not title or not title.strip():
            raise DomainValidationError("title", "Note title is required.")
        return cls(
            id=id,
            case_number=case_number.strip(),
            title=title.strip(),
            body=body,
            created_by=created_by,
            note_type=note_type,
            priority=priority,
        )

    # ================================================================== #
    # Content behaviour                                                    #
    # ================================================================== #

    def update(self, title: Optional[str], body: Optional[str], modified_by: str) -> None:
        if title is not None:
            if not title.strip():
                raise DomainValidationError("title", "Note title cannot be empty.")
            self.title = title.strip()
        if body is not None:
            self.body = body
        self.modified_by = modified_by
        self.modified_at = datetime.utcnow()

    # ================================================================== #
    # Status lifecycle                                                     #
    # ================================================================== #

    def archive(self, archived_by: str) -> None:
        """Move note to archived status."""
        if self.status == NoteStatus.ARCHIVED:
            return  # idempotent
        self.status = NoteStatus.ARCHIVED
        self._touch(archived_by)

    def restore(self, restored_by: str) -> None:
        """Restore an archived note back to active."""
        if self.status != NoteStatus.ARCHIVED:
            raise InvalidStatusTransitionError(
                self.id, str(self.status), str(NoteStatus.ACTIVE)
            )
        self.status = NoteStatus.ACTIVE
        self._touch(restored_by)

    def submit_for_approval(self, submitted_by: str) -> None:
        """Submit note for peer review / approval."""
        if self.status not in (NoteStatus.ACTIVE, NoteStatus.REJECTED):
            raise InvalidStatusTransitionError(
                self.id, str(self.status), str(NoteStatus.PENDING_APPROVAL)
            )
        self.status = NoteStatus.PENDING_APPROVAL
        self._touch(submitted_by)

    def approve(self, approved_by: str, comments: Optional[str] = None) -> None:
        """Approve a note that is pending review."""
        if self.status != NoteStatus.PENDING_APPROVAL:
            raise InvalidStatusTransitionError(
                self.id, str(self.status), str(NoteStatus.APPROVED)
            )
        self.status = NoteStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
        self.approval_comments = comments
        self._touch(approved_by)

    def reject(self, rejected_by: str, reason: str) -> None:
        """Reject a note under review, returning it to rejected state."""
        if self.status != NoteStatus.PENDING_APPROVAL:
            raise InvalidStatusTransitionError(
                self.id, str(self.status), str(NoteStatus.REJECTED)
            )
        self.status = NoteStatus.REJECTED
        self.approval_comments = reason
        self._touch(rejected_by)

    # ================================================================== #
    # Tag management                                                       #
    # ================================================================== #

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present (case-insensitive dedup)."""
        tag = tag.strip().lower()
        if not tag:
            raise DomainValidationError("tag", "Tag cannot be empty.")
        if tag not in [t.lower() for t in self.tags]:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag (case-insensitive). No-op if absent."""
        tag_lower = tag.strip().lower()
        self.tags = [t for t in self.tags if t.lower() != tag_lower]

    # ================================================================== #
    # Helpers                                                              #
    # ================================================================== #

    def _touch(self, actor: str) -> None:
        self.modified_by = actor
        self.modified_at = datetime.utcnow()

    @property
    def entity_id(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return (
            f"Note(id={self.id!r}, case={self.case_number!r}, "
            f"title={self.title!r}, status={self.status!r})"
        )
