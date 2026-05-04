"""domain/entities/investigative_lead.py — Investigative lead / tip entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.exceptions.domain_exceptions import DomainValidationError


@dataclass
class InvestigativeLead:
    id: int
    case_number: str
    name: str
    source: Optional[str] = None
    description: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        id: int,
        case_number: str,
        name: str,
        source: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "InvestigativeLead":
        if not case_number:
            raise DomainValidationError("case_number", "Case number is required.")
        if not name or not name.strip():
            raise DomainValidationError("name", "Lead name cannot be empty.")
        return cls(
            id=id,
            case_number=case_number,
            name=name.strip(),
            source=source,
            description=description,
        )

    def mark_completed(self, completed_by: str) -> None:
        self.completed = True
        self.completed_at = datetime.utcnow()
        self.completed_by = completed_by
        self.modified_at = datetime.utcnow()

    def reopen(self) -> None:
        self.completed = False
        self.completed_at = None
        self.completed_by = None
        self.modified_at = datetime.utcnow()

    @property
    def entity_id(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return (
            f"InvestigativeLead(id={self.id}, name={self.name!r}, "
            f"completed={self.completed})"
        )
