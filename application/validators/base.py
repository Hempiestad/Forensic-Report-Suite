"""application/validators/base.py — Lightweight validation framework.

Provides a :class:`ValidationResult` (errors bag) and a base
:class:`Validator` class.  No third-party library is required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional


# ── Result ────────────────────────────────────────────────────────────────

@dataclass
class ValidationError:
    field_name: str
    message: str


@dataclass
class ValidationResult:
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_error(self, field_name: str, message: str) -> None:
        self.errors.append(ValidationError(field_name, message))

    def raise_if_invalid(self) -> None:
        """Raise :class:`DtoValidationError` when there are validation errors."""
        if not self.is_valid:
            from application.validators.exceptions import DtoValidationError
            raise DtoValidationError(self)

    def __bool__(self) -> bool:
        return self.is_valid


# ── Base validator ────────────────────────────────────────────────────────

class Validator:
    """Base class for DTO validators."""

    def validate(self, dto: Any) -> ValidationResult:
        raise NotImplementedError

    # ── Rule helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _require(
        result: ValidationResult,
        value: Optional[str],
        field_name: str,
    ) -> None:
        if not value or not value.strip():
            result.add_error(field_name, f"{field_name} is required.")

    @staticmethod
    def _max_length(
        result: ValidationResult,
        value: Optional[str],
        field_name: str,
        max_len: int,
    ) -> None:
        if value and len(value) > max_len:
            result.add_error(field_name, f"{field_name} must be at most {max_len} characters.")

    @staticmethod
    def _min_length(
        result: ValidationResult,
        value: Optional[str],
        field_name: str,
        min_len: int,
    ) -> None:
        if value and len(value) < min_len:
            result.add_error(field_name, f"{field_name} must be at least {min_len} characters.")

    @staticmethod
    def _matches(
        result: ValidationResult,
        value: Optional[str],
        field_name: str,
        pattern: str,
    ) -> None:
        if value and not re.fullmatch(pattern, value):
            result.add_error(field_name, f"{field_name} contains invalid characters.")

    @staticmethod
    def _must_be_future(
        result: ValidationResult,
        value: Optional[datetime],
        field_name: str,
    ) -> None:
        if value is not None:
            now = datetime.now(timezone.utc) if value.tzinfo else datetime.utcnow()
            if value <= now:
                result.add_error(field_name, f"{field_name} must be a future date.")

    @staticmethod
    def _one_of(
        result: ValidationResult,
        value: Optional[str],
        field_name: str,
        allowed: List[str],
    ) -> None:
        if value is not None and value not in allowed:
            result.add_error(
                field_name,
                f"{field_name} must be one of: {', '.join(allowed)}.",
            )

    @staticmethod
    def _range(
        result: ValidationResult,
        value: Optional[float],
        field_name: str,
        min_val: float,
        max_val: float,
    ) -> None:
        if value is not None and not (min_val <= value <= max_val):
            result.add_error(field_name, f"{field_name} must be between {min_val} and {max_val}.")

    @staticmethod
    def _max_items(
        result: ValidationResult,
        items: Optional[list],
        field_name: str,
        max_count: int,
    ) -> None:
        if items and len(items) > max_count:
            result.add_error(field_name, f"{field_name} may contain at most {max_count} items.")
