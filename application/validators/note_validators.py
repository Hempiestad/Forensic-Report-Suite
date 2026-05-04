"""application/validators/note_validators.py — Note DTO validators."""
from __future__ import annotations

from application.dtos.note_dto import CreateNoteDto, UpdateNoteDto
from application.validators.base import ValidationResult, Validator

_VALID_NOTE_TYPES = [
    "observation", "investigation", "timeline", "task", "witness_statement",
    "evidence", "suspect", "location", "communication", "follow_up", "meeting", "analysis",
]
_VALID_PRIORITIES = ["low", "medium", "high", "critical"]
_VALID_VISIBILITIES = ["private", "team", "case_level", "public"]
_MAX_TAGS = 20
_MAX_TAG_LENGTH = 50


class CreateNoteDtoValidator(Validator):
    """Validates :class:`CreateNoteDto` before a note is created."""

    def validate(self, dto: CreateNoteDto) -> ValidationResult:
        result = ValidationResult()
        self._max_length(result, dto.case_number, "case_number", 50)
        self._require(result, dto.title, "title")
        self._min_length(result, dto.title, "title", 3)
        self._max_length(result, dto.title, "title", 200)
        self._require(result, dto.body, "body")
        self._one_of(result, dto.note_type, "note_type", _VALID_NOTE_TYPES)
        self._one_of(result, dto.priority, "priority", _VALID_PRIORITIES)
        # Tags
        tags = getattr(dto, "tags", None) or []
        self._max_items(result, tags, "tags", _MAX_TAGS)
        for tag in tags:
            if len(tag) > _MAX_TAG_LENGTH:
                result.add_error("tags", f"Tag '{tag}' exceeds {_MAX_TAG_LENGTH} characters.")
        return result


class UpdateNoteDtoValidator(Validator):
    """Validates :class:`UpdateNoteDto` before a note is updated."""

    def validate(self, dto: UpdateNoteDto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, dto.note_id, "note_id")
        if dto.title is not None:
            self._min_length(result, dto.title, "title", 3)
            self._max_length(result, dto.title, "title", 200)
        self._one_of(result, dto.note_type, "note_type", _VALID_NOTE_TYPES)
        self._one_of(result, dto.priority, "priority", _VALID_PRIORITIES)
        self._require(result, dto.modified_by, "modified_by")
        self._max_length(result, dto.modified_by, "modified_by", 100)
        # Require at least one field to update
        updatable = [dto.title, dto.body, dto.note_type, dto.priority]
        if all(v is None for v in updatable):
            result.add_error("dto", "At least one field must be provided for update.")
        return result
