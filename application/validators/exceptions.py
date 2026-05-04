"""application/validators/exceptions.py — Validation exception."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.validators.base import ValidationResult


class DtoValidationError(Exception):
    """Raised when a DTO fails validation.

    Carries the full :class:`ValidationResult` so callers can
    inspect individual field errors programmatically.
    """

    def __init__(self, result: "ValidationResult") -> None:
        self.result = result
        messages = "; ".join(f"{e.field_name}: {e.message}" for e in result.errors)
        super().__init__(f"Validation failed: {messages}")
