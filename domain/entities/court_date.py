"""domain/entities/court_date.py — Court date attached to a case."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.exceptions.domain_exceptions import DomainValidationError


@dataclass
class CourtDate:
    id: int
    case_number: str
    date_type: str         # e.g. "trial", "sentencing", "hearing", "motion"
    court_date: datetime
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        id: int,
        case_number: str,
        date_type: str,
        court_date: datetime,
        location: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> "CourtDate":
        if not case_number:
            raise DomainValidationError("case_number", "Case number is required.")
        if not date_type:
            raise DomainValidationError("date_type", "Date type is required.")
        if court_date is None:
            raise DomainValidationError("court_date", "Court date is required.")
        return cls(
            id=id,
            case_number=case_number,
            date_type=date_type,
            court_date=court_date,
            location=location,
            notes=notes,
        )

    @property
    def entity_id(self) -> str:
        return str(self.id)

    @property
    def days_until(self) -> int:
        delta = self.court_date - datetime.utcnow()
        return delta.days

    @property
    def is_upcoming(self) -> bool:
        return self.days_until > 0

    @property
    def is_overdue(self) -> bool:
        return self.days_until < 0

    def __repr__(self) -> str:
        return (
            f"CourtDate(id={self.id}, type={self.date_type!r}, "
            f"date={self.court_date.date()}, case={self.case_number!r})"
        )
