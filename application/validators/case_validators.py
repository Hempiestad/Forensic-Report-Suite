"""application/validators/case_validators.py — Case DTO validators."""
from __future__ import annotations

from application.dtos.case_dto import CreateCaseDto, UpdateCaseDto
from application.validators.base import ValidationResult, Validator

_CASE_NUMBER_PATTERN = r"[a-zA-Z0-9\-_]+"
_VALID_CASE_STATUSES = [
    "draft",
    "under_investigation",
    "pending_review",
    "under_legal_review",
    "closed",
    "archived",
]


class CreateCaseDtoValidator(Validator):
    """Validates :class:`CreateCaseDto` before case creation."""

    def validate(self, dto: CreateCaseDto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, dto.case_number, "case_number")
        self._min_length(result, dto.case_number, "case_number", 3)
        self._max_length(result, dto.case_number, "case_number", 50)
        self._matches(result, dto.case_number, "case_number", _CASE_NUMBER_PATTERN)
        self._max_length(result, dto.assigned_to, "assigned_to", 100)
        self._max_length(result, dto.created_by, "created_by", 100)
        return result


class UpdateCaseDtoValidator(Validator):
    """Validates :class:`UpdateCaseDto` before case update."""

    def validate(self, dto: UpdateCaseDto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, dto.case_number, "case_number")
        self._max_length(result, dto.assigned_to, "assigned_to", 100)
        self._max_length(result, dto.review_comments, "review_comments", 5000)
        self._must_be_future(result, dto.trial_date, "trial_date")
        self._must_be_future(result, dto.sentencing_date, "sentencing_date")
        return result


class ChangeCaseStatusDtoValidator(Validator):
    """Validates status-change requests."""

    def validate(self, dto) -> ValidationResult:  # accepts any object with .target_status / .comments
        result = ValidationResult()
        self._require(result, getattr(dto, "target_status", None), "target_status")
        self._one_of(result, getattr(dto, "target_status", None), "target_status", _VALID_CASE_STATUSES)
        self._max_length(result, getattr(dto, "comments", None), "comments", 5000)
        return result
