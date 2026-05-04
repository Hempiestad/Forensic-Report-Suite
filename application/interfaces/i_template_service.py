"""application/interfaces/i_template_service.py — Full template service contract (35 methods)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ITemplateService(ABC):

    # ── CRUD ─────────────────────────────────────────────────────────────

    @abstractmethod
    def create_template(self, dto) -> object:
        """Create a new template. Returns TemplateDto."""

    @abstractmethod
    def get_template_by_id(self, template_id: int) -> Optional[object]:
        """Return TemplateDto or None."""

    @abstractmethod
    def get_template_by_name(self, name: str) -> Optional[object]:
        """Return TemplateDto or None."""

    @abstractmethod
    def get_all_templates(self) -> List[object]:
        """Return list of all TemplateDto."""

    @abstractmethod
    def get_published_templates(self) -> List[object]:
        """Return only published TemplateDto."""

    @abstractmethod
    def update_template(self, dto) -> object:
        """Update template content, creates a new version. Returns TemplateDto."""

    @abstractmethod
    def delete_template(self, template_id: int, deleted_by: str) -> None:
        """Delete a template (with audit)."""

    @abstractmethod
    def publish_template(self, template_id: int, published_by: str) -> None:
        """Mark template as published."""

    @abstractmethod
    def unpublish_template(self, template_id: int, unpublished_by: str) -> None:
        """Withdraw from published state."""

    # ── Placeholders ─────────────────────────────────────────────────────

    @abstractmethod
    def add_placeholder(self, template_id: int, placeholder_dto) -> None:
        """Add a placeholder to a template."""

    @abstractmethod
    def remove_placeholder(self, template_id: int, placeholder_name: str) -> None:
        """Remove a placeholder from a template."""

    @abstractmethod
    def get_placeholders(self, template_id: int) -> List[object]:
        """Return list of TemplatePlaceholderDto."""

    @abstractmethod
    def auto_detect_placeholders(self, template_id: int) -> List[str]:
        """Scan template HTML and auto-register found placeholders."""

    @abstractmethod
    def validate_template_html(self, html: str) -> List[str]:
        """Validate HTML well-formedness. Returns list of error messages."""

    # ── Rendering ────────────────────────────────────────────────────────

    @abstractmethod
    def render_template(self, template_id: int, values: Dict[str, Any]) -> str:
        """Render template substituting placeholder values."""

    @abstractmethod
    def render_template_by_name(self, name: str, values: Dict[str, Any]) -> str:
        """Render by template name."""

    @abstractmethod
    def generate_preview(self, template_id: int) -> str:
        """Render with sample values (no validation errors expected)."""

    @abstractmethod
    def validate_placeholder_values(self, template_id: int, values: Dict[str, Any]) -> List[str]:
        """Validate a set of values against template placeholder rules."""

    # ── Category & filtering ─────────────────────────────────────────────

    @abstractmethod
    def get_templates_by_category(self, category: str) -> List[object]:
        """Return templates in a specific category."""

    @abstractmethod
    def get_templates_by_tag(self, tag: str) -> List[object]:
        """Return templates with a specific tag."""

    @abstractmethod
    def get_recent_templates(self, limit: int = 10) -> List[object]:
        """Return recently used templates."""

    @abstractmethod
    def get_most_used_templates(self, limit: int = 10) -> List[object]:
        """Return templates ranked by usage count."""

    @abstractmethod
    def get_favorite_templates(self, username: str) -> List[object]:
        """Return templates marked as favourites by a user."""

    @abstractmethod
    def add_to_favorites(self, template_id: int, username: str) -> None:
        """Mark template as a user favourite."""

    @abstractmethod
    def remove_from_favorites(self, template_id: int, username: str) -> None:
        """Remove from user favourites."""

    # ── Search ────────────────────────────────────────────────────────────

    @abstractmethod
    def search_templates(self, query: str) -> List[object]:
        """Full-text search across name, description, tags, and content."""

    # ── Versioning ───────────────────────────────────────────────────────

    @abstractmethod
    def get_version_history(self, template_id: int) -> List[object]:
        """Return list of TemplateVersionDto."""

    @abstractmethod
    def get_template_version(self, template_id: int, version_number: int) -> Optional[object]:
        """Return a specific TemplateVersionDto."""

    @abstractmethod
    def rollback_to_version(self, template_id: int, version_number: int, rolled_back_by: str) -> None:
        """Restore template content to a specific version."""

    # ── Usage tracking ────────────────────────────────────────────────────

    @abstractmethod
    def record_usage(self, template_id: int) -> None:
        """Increment usage counter and stamp last_used_at."""

    @abstractmethod
    def get_statistics(self, template_id: int) -> dict:
        """Return usage statistics for a single template."""

    @abstractmethod
    def get_all_statistics(self) -> List[dict]:
        """Return usage statistics for all templates."""

    # ── Import / Export ───────────────────────────────────────────────────

    @abstractmethod
    def import_from_docx(self, file_path: str, imported_by: str) -> object:
        """Import template from a .docx file. Returns TemplateDto."""

    @abstractmethod
    def export_to_docx(self, template_id: int, output_path: str) -> None:
        """Export template as .docx file."""

    @abstractmethod
    def import_from_html(self, html: str, name: str, imported_by: str) -> object:
        """Import template from raw HTML string."""

    @abstractmethod
    def export_to_html(self, template_id: int) -> str:
        """Return template HTML content."""

    @abstractmethod
    def import_from_json(self, json_data: dict, imported_by: str) -> object:
        """Import template from a JSON export dict."""

    @abstractmethod
    def export_to_json(self, template_id: int) -> dict:
        """Serialise template to a JSON-compatible dict."""

    # ── Defaults ─────────────────────────────────────────────────────────

    @abstractmethod
    def get_or_create_swgde_nist_template(self) -> object:
        """Return (or create) the built-in SWGDE/NIST template."""

    @abstractmethod
    def get_or_create_basic_template(self) -> object:
        """Return (or create) the built-in blank template."""

    @abstractmethod
    def initialize_default_templates(self) -> None:
        """Seed all default templates on first run."""

    # ── Composition ──────────────────────────────────────────────────────

    @abstractmethod
    def clone_template(self, template_id: int, new_name: str, cloned_by: str) -> object:
        """Duplicate a template under a new name. Returns TemplateDto."""

    @abstractmethod
    def get_or_create_mobile_forensics_template(self) -> object:
        """Return (or create) the built-in Mobile Forensics template."""

    @abstractmethod
    def set_parent_template(self, template_id: int, parent_template_id: Optional[int], set_by: str) -> object:
        """Set or clear the parent template for template inheritance. Returns updated TemplateDto."""

    @abstractmethod
    def export_templates_as_zip(self, template_ids: List[int], output_path: str) -> None:
        """Export a collection of templates to a ZIP archive at output_path."""

    @abstractmethod
    def import_templates_from_zip(self, zip_path: str, imported_by: str) -> List[object]:
        """Import templates from a ZIP archive. Returns list of TemplateDto."""
