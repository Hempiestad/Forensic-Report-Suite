"""domain/entities/template_version.py — Immutable snapshot of a template version."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class TemplateVersion:
    """Immutable snapshot of template HTML at a specific version number."""

    version_number: int
    html_content: str
    created_at: datetime
    created_by: str
    notes: Optional[str] = None

    @classmethod
    def create(
        cls,
        version_number: int,
        html_content: str,
        created_by: str,
        notes: Optional[str] = None,
    ) -> "TemplateVersion":
        return cls(
            version_number=version_number,
            html_content=html_content,
            created_at=datetime.utcnow(),
            created_by=created_by,
            notes=notes,
        )

    def __repr__(self) -> str:
        return (
            f"TemplateVersion(v{self.version_number}, "
            f"by={self.created_by!r}, at={self.created_at.date()})"
        )
