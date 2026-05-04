"""application/dtos/template_dto.py — Template data transfer objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class TemplatePlaceholderDto:
    name: str
    placeholder_type: str
    description: str
    is_required: bool
    default_value: Optional[str] = None
    sample_value: Optional[str] = None
    token: str = ""

    def __post_init__(self) -> None:
        if not self.token:
            self.token = f"{{{self.name}}}"


@dataclass
class TemplateVersionDto:
    version_number: int
    created_at: datetime
    created_by: str
    notes: str


@dataclass
class TemplateDto:
    """Read model returned from ITemplateService."""

    template_id: int
    name: str
    category: str
    description: str
    is_published: bool
    is_system_template: bool
    created_by: str
    created_at: datetime
    modified_at: Optional[datetime]
    modified_by: Optional[str]
    current_version: int
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    placeholders: List[TemplatePlaceholderDto] = field(default_factory=list)


@dataclass
class CreateTemplateDto:
    """Input model for creating a new template."""

    name: str
    category: str
    html_content: str
    created_by: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    is_published: bool = False


@dataclass
class UpdateTemplateDto:
    """Input model for updating a template (creates a new version)."""

    template_id: int
    html_content: str
    updated_by: str
    version_notes: str = ""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
