"""application/validators/evidence_validators.py — Evidence DTO validators."""
from __future__ import annotations

from application.validators.base import ValidationResult, Validator

_VALID_IMAGING_STATUSES = ["not_imaged", "in_progress", "completed", "failed"]


class CreateEvidenceDtoValidator(Validator):
    """Validates CreateEvidenceDto before evidence is added."""

    def validate(self, dto) -> ValidationResult:
        result = ValidationResult()
        self._require(result, getattr(dto, "case_number", None), "case_number")
        self._max_length(result, getattr(dto, "evidence_item_number", None), "evidence_item_number", 50)
        self._max_length(result, getattr(dto, "item_type", None), "item_type", 50)
        self._max_length(result, getattr(dto, "physical_description", None), "physical_description", 1000)
        return result


class UpdateEvidenceDtoValidator(Validator):
    """Validates UpdateEvidenceDto before evidence update."""

    def validate(self, dto) -> ValidationResult:
        result = ValidationResult()
        imaging_status = getattr(dto, "imaging_status", None)
        self._one_of(result, imaging_status, "imaging_status", _VALID_IMAGING_STATUSES)
        self._max_length(result, getattr(dto, "evidence_found", None), "evidence_found", 5000)
        return result
