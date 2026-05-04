"""application/validators/legal_validators.py — Legal process and court date validators."""
from __future__ import annotations

from application.validators.base import ValidationResult, Validator


class CreateLegalProcessDtoValidator(Validator):
    """Validates CreateLegalProcessDto before a legal process is created."""

    def validate(self, dto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, getattr(dto, "case_number", None), "case_number")
        self._max_length(result, getattr(dto, "process_type", None), "process_type", 100)
        self._max_length(result, getattr(dto, "provider", None), "provider", 100)
        self._must_be_future(result, getattr(dto, "due_date", None), "due_date")
        return result


class CreateInvestigativeLeadDtoValidator(Validator):
    """Validates CreateLeadDto before an investigative lead is created."""

    def validate(self, dto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, getattr(dto, "case_number", None), "case_number")
        self._require(result, getattr(dto, "name", None), "name")
        self._max_length(result, getattr(dto, "name", None), "name", 200)
        self._max_length(result, getattr(dto, "description", None), "description", 2000)
        return result


class CreateCourtDateDtoValidator(Validator):
    """Validates CreateCourtDateDto before a court date is added."""

    def validate(self, dto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, getattr(dto, "case_number", None), "case_number")
        self._max_length(result, getattr(dto, "date_type", None), "date_type", 100)
        self._must_be_future(result, getattr(dto, "court_date", None), "court_date")
        return result
