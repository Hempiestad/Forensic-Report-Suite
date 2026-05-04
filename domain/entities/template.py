"""
domain/entities/template.py — Template aggregate with versioning, placeholders, and audit.

Mirrors C# Template.cs entity — the most feature-rich domain class
in this codebase, replacing the simple JSON-backed templates.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from domain.enums.template_category import TemplateCategory
from domain.exceptions.domain_exceptions import (
    DomainValidationError,
    TemplatePlaceholderError,
)
from domain.entities.template_placeholder import TemplatePlaceholder
from domain.entities.template_version import TemplateVersion


@dataclass
class Template:
    """
    Template aggregate root.

    Lifecycle:
      created → (edited) → published → (deprecated / archived)

    Versioning:
      Every time html_content changes, a new TemplateVersion snapshot
      is appended to _versions. Rollback restores a previous snapshot.
    """

    # ── Identity ─────────────────────────────────────────────────────────
    id: int
    name: str
    category: TemplateCategory

    # ── Content ──────────────────────────────────────────────────────────
    html_content: str
    description: Optional[str] = None

    # ── State ────────────────────────────────────────────────────────────
    is_published: bool = False
    is_default: bool = False
    is_favorite: bool = False

    # ── Versioning ───────────────────────────────────────────────────────
    version_number: int = 1
    _versions: List[TemplateVersion] = field(default_factory=list, repr=False, compare=False)

    # ── Placeholders ─────────────────────────────────────────────────────
    _placeholders: List[TemplatePlaceholder] = field(default_factory=list, repr=False, compare=False)

    # ── Tagging / discovery ──────────────────────────────────────────────
    tags: List[str] = field(default_factory=list)

    # ── Usage stats ──────────────────────────────────────────────────────
    usage_count: int = 0
    last_used_at: Optional[datetime] = None

    # ── Composition (optional parent) ────────────────────────────────────
    parent_template_id: Optional[int] = None

    # ── Audit ────────────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    modified_at: datetime = field(default_factory=datetime.utcnow)
    modified_by: Optional[str] = None

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(
        cls,
        id: int,
        name: str,
        category: TemplateCategory,
        html_content: str,
        created_by: str,
        description: Optional[str] = None,
    ) -> "Template":
        if not name or not name.strip():
            raise DomainValidationError("name", "Template name cannot be empty.")
        if not html_content or not html_content.strip():
            raise DomainValidationError("html_content", "Template HTML cannot be empty.")

        tmpl = cls(
            id=id,
            name=name.strip(),
            category=category,
            html_content=html_content,
            description=description,
            created_by=created_by,
        )
        # Record initial version
        tmpl._versions.append(
            TemplateVersion.create(
                version_number=1,
                html_content=html_content,
                created_by=created_by,
                notes="Initial version",
            )
        )
        return tmpl

    # ================================================================== #
    # Versioning                                                           #
    # ================================================================== #

    def create_new_version(
        self, new_html: str, changed_by: str, notes: Optional[str] = None
    ) -> None:
        """Bump version, save snapshot, update content."""
        if not new_html or not new_html.strip():
            raise DomainValidationError("html_content", "New HTML content cannot be empty.")
        self.version_number += 1
        self._versions.append(
            TemplateVersion.create(
                version_number=self.version_number,
                html_content=new_html,
                created_by=changed_by,
                notes=notes,
            )
        )
        self.html_content = new_html
        self._touch(changed_by)

    def rollback_to_version(self, version_number: int, changed_by: str) -> None:
        """Restore html_content to a specific historical version."""
        snapshot = self.get_version(version_number)
        if snapshot is None:
            raise DomainValidationError(
                "version_number", f"Version {version_number} does not exist."
            )
        self.html_content = snapshot.html_content
        self.version_number += 1
        self._versions.append(
            TemplateVersion.create(
                version_number=self.version_number,
                html_content=snapshot.html_content,
                created_by=changed_by,
                notes=f"Rolled back to v{version_number}",
            )
        )
        self._touch(changed_by)

    def get_version(self, version_number: int) -> Optional[TemplateVersion]:
        return next((v for v in self._versions if v.version_number == version_number), None)

    @property
    def version_history(self) -> List[TemplateVersion]:
        return list(self._versions)

    @property
    def latest_version(self) -> Optional[TemplateVersion]:
        return self._versions[-1] if self._versions else None

    # ================================================================== #
    # Placeholders                                                         #
    # ================================================================== #

    @property
    def placeholders(self) -> List[TemplatePlaceholder]:
        return list(self._placeholders)

    def add_placeholder(self, placeholder: TemplatePlaceholder) -> None:
        if any(p.name == placeholder.name for p in self._placeholders):
            raise DomainValidationError("placeholder", f"Placeholder '{placeholder.name}' already exists.")
        self._placeholders.append(placeholder)

    def remove_placeholder(self, name: str) -> None:
        self._placeholders = [p for p in self._placeholders if p.name != name]

    def get_placeholder(self, name: str) -> Optional[TemplatePlaceholder]:
        return next((p for p in self._placeholders if p.name == name), None)

    def auto_detect_placeholders(self) -> List[str]:
        """Scan html_content for {token} patterns and return new names found."""
        found = re.findall(r"\{(\w+)\}", self.html_content)
        new_names = []
        for name in dict.fromkeys(found):  # deduplicate, preserve order
            if not any(p.name == name for p in self._placeholders):
                self._placeholders.append(
                    TemplatePlaceholder(name=name, description=name.replace("_", " ").title())
                )
                new_names.append(name)
        return new_names

    def validate_placeholder_values(self, values: Dict[str, Any]) -> List[str]:
        """Validate supplied values against placeholder rules. Returns error messages."""
        errors: List[str] = []
        for ph in self._placeholders:
            try:
                ph.validate(values.get(ph.name))
            except TemplatePlaceholderError as exc:
                errors.append(str(exc))
        return errors

    # ================================================================== #
    # Rendering                                                            #
    # ================================================================== #

    def render(self, values: Dict[str, Any]) -> str:
        """Substitute placeholder tokens with provided values."""
        errors = self.validate_placeholder_values(values)
        if errors:
            raise DomainValidationError("placeholders", "; ".join(errors))

        result = self.html_content
        for ph in self._placeholders:
            raw = values.get(ph.name)
            formatted = ph.format_value(raw) if raw is not None else (ph.default_value or "")
            result = result.replace(ph.token, formatted)
        return result

    def generate_preview(self) -> str:
        """Render with sample values (no validation errors)."""
        sample_values = {
            ph.name: (ph.sample_value or ph.default_value or f"[{ph.name}]")
            for ph in self._placeholders
        }
        result = self.html_content
        for ph in self._placeholders:
            result = result.replace(ph.token, sample_values[ph.name])
        return result

    # ================================================================== #
    # Usage                                                                #
    # ================================================================== #

    def record_usage(self) -> None:
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def publish(self, changed_by: str) -> None:
        self.is_published = True
        self._touch(changed_by)

    def unpublish(self, changed_by: str) -> None:
        self.is_published = False
        self._touch(changed_by)

    def add_tag(self, tag: str) -> None:
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        self.tags = [t for t in self.tags if t != tag.strip().lower()]

    # ================================================================== #
    # Properties                                                           #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return str(self.id)

    @property
    def placeholder_count(self) -> int:
        return len(self._placeholders)

    @property
    def required_placeholder_names(self) -> List[str]:
        return [p.name for p in self._placeholders if p.is_required]

    # ================================================================== #
    # Helpers                                                              #
    # ================================================================== #

    def _touch(self, changed_by: Optional[str] = None) -> None:
        self.modified_at = datetime.utcnow()
        if changed_by:
            self.modified_by = changed_by

    def __repr__(self) -> str:
        return (
            f"Template(id={self.id}, name={self.name!r}, "
            f"category={self.category!r}, v{self.version_number})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Template):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
