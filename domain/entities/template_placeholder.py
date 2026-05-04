"""
domain/entities/template_placeholder.py — Typed placeholder value object.

Mirrors C# TemplatePlaceholder.cs — each placeholder has a type,
validation pattern, required flag, and sample/default values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from domain.exceptions.domain_exceptions import TemplatePlaceholderError


class PlaceholderType(str, Enum):
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    CURRENCY = "currency"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    REFERENCE = "reference"
    BOOLEAN = "boolean"
    HTML = "html"


@dataclass(frozen=True)
class TemplatePlaceholder:
    """Immutable value object describing one template variable."""

    name: str                               # e.g. "case_number"
    description: str
    placeholder_type: PlaceholderType = PlaceholderType.STRING
    is_required: bool = True
    default_value: Optional[str] = None
    sample_value: Optional[str] = None
    validation_pattern: Optional[str] = None  # Regex, if any
    help_text: Optional[str] = None

    # ================================================================== #
    # Factories                                                            #
    # ================================================================== #

    @classmethod
    def string(cls, name: str, description: str, required: bool = True, **kw) -> "TemplatePlaceholder":
        return cls(name=name, description=description, placeholder_type=PlaceholderType.STRING, is_required=required, **kw)

    @classmethod
    def date(cls, name: str, description: str, required: bool = True, **kw) -> "TemplatePlaceholder":
        return cls(name=name, description=description, placeholder_type=PlaceholderType.DATE, is_required=required, **kw)

    @classmethod
    def number(cls, name: str, description: str, required: bool = False, **kw) -> "TemplatePlaceholder":
        return cls(name=name, description=description, placeholder_type=PlaceholderType.NUMBER, is_required=required, **kw)

    @classmethod
    def email(cls, name: str, description: str, required: bool = False, **kw) -> "TemplatePlaceholder":
        return cls(name=name, description=description, placeholder_type=PlaceholderType.EMAIL,
                   is_required=required, validation_pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", **kw)

    # ================================================================== #
    # Token                                                                #
    # ================================================================== #

    @property
    def token(self) -> str:
        """Returns the in-template token string, e.g. '{case_number}'."""
        return "{" + self.name + "}"

    # ================================================================== #
    # Validation                                                           #
    # ================================================================== #

    def validate(self, value: Any) -> None:
        """Raise TemplatePlaceholderError if *value* fails domain rules."""
        if value is None or str(value).strip() == "":
            if self.is_required:
                raise TemplatePlaceholderError(self.name, "Required placeholder has no value.")
            return

        str_value = str(value).strip()

        if self.placeholder_type == PlaceholderType.EMAIL:
            pattern = self.validation_pattern or r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            if not re.match(pattern, str_value):
                raise TemplatePlaceholderError(self.name, f"Invalid email address: {str_value!r}")

        elif self.placeholder_type == PlaceholderType.NUMBER:
            try:
                float(str_value)
            except ValueError:
                raise TemplatePlaceholderError(self.name, f"Expected a number, got: {str_value!r}")

        elif self.placeholder_type == PlaceholderType.DATE:
            # Accept ISO date strings; full parse left to service layer
            date_re = r"^\d{4}-\d{2}-\d{2}"
            if not re.match(date_re, str_value):
                raise TemplatePlaceholderError(self.name, f"Expected ISO date (YYYY-MM-DD), got: {str_value!r}")

        if self.validation_pattern:
            if not re.match(self.validation_pattern, str_value):
                raise TemplatePlaceholderError(
                    self.name, f"Value does not match validation pattern {self.validation_pattern!r}"
                )

    # ================================================================== #
    # Formatting                                                           #
    # ================================================================== #

    def format_value(self, value: Any) -> str:
        """Return a display-friendly formatted string for *value*."""
        if value is None:
            return self.default_value or ""
        str_value = str(value).strip()
        if self.placeholder_type == PlaceholderType.CURRENCY:
            try:
                return f"${float(str_value):,.2f}"
            except ValueError:
                return str_value
        return str_value
