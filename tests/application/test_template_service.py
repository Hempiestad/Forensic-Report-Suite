"""
tests/application/test_template_service.py

Unit tests for TemplateService (Phase 5).
Uses in-memory fakes — no SQLite, no PyQt5.
"""
from __future__ import annotations

import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from application.dtos.template_dto import (
    CreateTemplateDto,
    TemplatePlaceholderDto,
    UpdateTemplateDto,
)
from application.services.template_service import TemplateService, _HTMLValidator
from domain.enums.template_category import TemplateCategory
from domain.exceptions.domain_exceptions import DomainValidationError


# ---------------------------------------------------------------------------
# In-memory fake repo
# ---------------------------------------------------------------------------

class _FakeTemplateRepo:
    def __init__(self):
        self._store: dict = {}

    def get_by_id(self, entity_id: str):
        return self._store.get(int(entity_id))

    def get_all(self) -> list:
        return list(self._store.values())

    def add(self, entity) -> None:
        self._store[entity.id] = entity

    def update(self, entity) -> None:
        self._store[entity.id] = entity

    def delete(self, entity_id: str) -> None:
        self._store.pop(int(entity_id), None)

    def exists(self, entity_id: str) -> bool:
        return int(entity_id) in self._store

    def get_by_name(self, name: str):
        for t in self._store.values():
            if t.name == name:
                return t
        return None

    def get_published(self) -> list:
        return [t for t in self._store.values() if t.is_published]

    def get_by_category(self, category: str) -> list:
        return [t for t in self._store.values() if t.category.value == category]

    def search(self, query: str) -> list:
        q = query.lower()
        return [
            t for t in self._store.values()
            if q in t.name.lower() or q in (t.description or "").lower()
        ]


class _FakeAudit:
    def __init__(self):
        self.events: list = []

    def log_event(self, *, event_type, description, actor, entity_id=None, metadata=None):
        self.events.append({
            "type": event_type,
            "desc": description,
            "actor": actor,
            "entity_id": entity_id,
            "meta": metadata,
        })


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def repo():
    return _FakeTemplateRepo()


@pytest.fixture
def audit():
    return _FakeAudit()


@pytest.fixture
def svc(repo, audit):
    return TemplateService(repo, audit)


def _create_dto(**overrides) -> CreateTemplateDto:
    defaults = dict(
        name="Test Template",
        category=TemplateCategory.BASIC.value,
        html_content="<p>Hello {name}</p>",
        created_by="alice",
    )
    defaults.update(overrides)
    return CreateTemplateDto(**defaults)


# ===========================================================================
# CRUD
# ===========================================================================

class TestCreate:
    def test_returns_dto_with_correct_fields(self, svc):
        dto = svc.create_template(_create_dto())
        assert dto.name == "Test Template"
        assert dto.category == TemplateCategory.BASIC.value
        assert dto.current_version == 1
        assert dto.is_published is False

    def test_empty_name_raises(self, svc):
        with pytest.raises(DomainValidationError, match="name"):
            svc.create_template(_create_dto(name=""))

    def test_empty_html_raises(self, svc):
        with pytest.raises(DomainValidationError, match="html_content"):
            svc.create_template(_create_dto(html_content=""))

    def test_duplicate_name_raises(self, svc):
        svc.create_template(_create_dto())
        with pytest.raises(DomainValidationError, match="already exists"):
            svc.create_template(_create_dto())

    def test_audit_event_fired(self, svc, audit):
        svc.create_template(_create_dto())
        assert any(e["type"] == "TEMPLATE_CREATED" for e in audit.events)

    def test_tags_stored(self, svc):
        dto = svc.create_template(_create_dto(tags=["forensics", "report"]))
        assert "forensics" in dto.tags
        assert "report" in dto.tags

    def test_is_published_flag(self, svc):
        dto = svc.create_template(_create_dto(is_published=True))
        assert dto.is_published is True


class TestGetById:
    def test_returns_dto(self, svc):
        created = svc.create_template(_create_dto())
        got = svc.get_template_by_id(created.template_id)
        assert got is not None
        assert got.template_id == created.template_id

    def test_returns_none_for_missing(self, svc):
        assert svc.get_template_by_id(9999) is None


class TestGetByName:
    def test_finds_template(self, svc):
        svc.create_template(_create_dto(name="Alpha"))
        got = svc.get_template_by_name("Alpha")
        assert got is not None
        assert got.name == "Alpha"

    def test_returns_none_for_missing(self, svc):
        assert svc.get_template_by_name("Nope") is None


class TestGetAll:
    def test_empty_repo(self, svc):
        assert svc.get_all_templates() == []

    def test_multiple(self, svc):
        svc.create_template(_create_dto(name="A"))
        svc.create_template(_create_dto(name="B"))
        assert len(svc.get_all_templates()) == 2


class TestGetPublished:
    def test_only_published(self, svc):
        svc.create_template(_create_dto(name="Draft"))
        svc.create_template(_create_dto(name="Live", is_published=True))
        results = svc.get_published_templates()
        assert len(results) == 1
        assert results[0].name == "Live"


class TestUpdate:
    def test_creates_new_version(self, svc):
        created = svc.create_template(_create_dto())
        upd = UpdateTemplateDto(
            template_id=created.template_id,
            html_content="<p>Updated</p>",
            updated_by="bob",
        )
        updated = svc.update_template(upd)
        assert updated.current_version == 2

    def test_empty_html_raises(self, svc):
        created = svc.create_template(_create_dto())
        upd = UpdateTemplateDto(template_id=created.template_id, html_content="", updated_by="bob")
        with pytest.raises(DomainValidationError):
            svc.update_template(upd)

    def test_missing_id_raises(self, svc):
        with pytest.raises(DomainValidationError):
            svc.update_template(UpdateTemplateDto(template_id=9999, html_content="<p>x</p>", updated_by="bob"))

    def test_audit_event_fired(self, svc, audit):
        created = svc.create_template(_create_dto())
        svc.update_template(UpdateTemplateDto(template_id=created.template_id, html_content="<p>v2</p>", updated_by="bob"))
        assert any(e["type"] == "TEMPLATE_UPDATED" for e in audit.events)

    def test_tags_updated(self, svc):
        created = svc.create_template(_create_dto())
        upd = UpdateTemplateDto(
            template_id=created.template_id,
            html_content="<p>v2</p>",
            updated_by="bob",
            tags=["evidence"],
        )
        result = svc.update_template(upd)
        assert "evidence" in result.tags


class TestDelete:
    def test_removes_template(self, svc):
        created = svc.create_template(_create_dto())
        svc.delete_template(created.template_id, "alice")
        assert svc.get_template_by_id(created.template_id) is None

    def test_missing_raises(self, svc):
        with pytest.raises(DomainValidationError):
            svc.delete_template(9999, "alice")

    def test_audit_event_fired(self, svc, audit):
        created = svc.create_template(_create_dto())
        svc.delete_template(created.template_id, "alice")
        assert any(e["type"] == "TEMPLATE_DELETED" for e in audit.events)


class TestPublishUnpublish:
    def test_publish_sets_flag(self, svc):
        created = svc.create_template(_create_dto())
        svc.publish_template(created.template_id, "alice")
        got = svc.get_template_by_id(created.template_id)
        assert got.is_published is True

    def test_unpublish_clears_flag(self, svc):
        created = svc.create_template(_create_dto(is_published=True))
        svc.unpublish_template(created.template_id, "alice")
        got = svc.get_template_by_id(created.template_id)
        assert got.is_published is False

    def test_publish_audit(self, svc, audit):
        created = svc.create_template(_create_dto())
        svc.publish_template(created.template_id, "alice")
        assert any(e["type"] == "TEMPLATE_PUBLISHED" for e in audit.events)


# ===========================================================================
# Placeholders
# ===========================================================================

class TestPlaceholders:
    def _ph_dto(self, name="case_number") -> TemplatePlaceholderDto:
        return TemplatePlaceholderDto(
            name=name,
            placeholder_type="string",
            description="Case number",
            is_required=True,
        )

    def test_add_and_get(self, svc):
        created = svc.create_template(_create_dto())
        svc.add_placeholder(created.template_id, self._ph_dto())
        phs = svc.get_placeholders(created.template_id)
        assert any(p.name == "case_number" for p in phs)

    def test_remove_placeholder(self, svc):
        created = svc.create_template(_create_dto())
        svc.add_placeholder(created.template_id, self._ph_dto())
        svc.remove_placeholder(created.template_id, "case_number")
        phs = svc.get_placeholders(created.template_id)
        assert not any(p.name == "case_number" for p in phs)

    def test_auto_detect_from_content(self, svc):
        created = svc.create_template(_create_dto(html_content="<p>{examiner_name} - {case_id}</p>"))
        detected = svc.auto_detect_placeholders(created.template_id)
        assert "examiner_name" in detected
        assert "case_id" in detected


# ===========================================================================
# HTML Validation
# ===========================================================================

class TestHTMLValidation:
    def test_valid_html_no_errors(self, svc):
        errors = svc.validate_template_html("<p>Hello <strong>world</strong></p>")
        assert errors == []

    def test_unclosed_tag_detected(self, svc):
        errors = svc.validate_template_html("<p>Hello <strong>world</p>")
        assert len(errors) > 0

    def test_empty_html_error(self, svc):
        errors = svc.validate_template_html("")
        assert len(errors) > 0

    def test_void_tags_ok(self, svc):
        errors = svc.validate_template_html("<p>Line<br>Break<hr>End</p>")
        assert errors == []


class TestHTMLValidatorDirect:
    def test_nested_correct(self):
        v = _HTMLValidator()
        assert v.check("<div><p>text</p></div>") == []

    def test_wrong_close(self):
        v = _HTMLValidator()
        errors = v.check("<div><p>text</div></p>")
        assert len(errors) > 0


# ===========================================================================
# Rendering
# ===========================================================================

class TestRendering:
    def test_render_replaces_placeholders(self, svc):
        created = svc.create_template(_create_dto(html_content="<p>Hello {name}</p>"))
        result = svc.render_template(created.template_id, {"name": "Alice"})
        assert "Alice" in result

    def test_render_by_name(self, svc):
        svc.create_template(_create_dto(name="MyTemplate", html_content="<p>{greeting}</p>"))
        result = svc.render_template_by_name("MyTemplate", {"greeting": "Hi"})
        assert "Hi" in result

    def test_render_by_name_missing_raises(self, svc):
        with pytest.raises(DomainValidationError):
            svc.render_template_by_name("Ghost", {})

    def test_generate_preview(self, svc):
        created = svc.create_template(_create_dto(html_content="<p>{name}</p>"))
        preview = svc.generate_preview(created.template_id)
        assert isinstance(preview, str)
        assert len(preview) > 0

    def test_render_increments_usage_count(self, svc):
        created = svc.create_template(_create_dto(html_content="<p>{x}</p>"))
        svc.render_template(created.template_id, {"x": "v"})
        got = svc.get_template_by_id(created.template_id)
        assert got.usage_count >= 1


# ===========================================================================
# Category / tag / recent filtering
# ===========================================================================

class TestFiltering:
    def test_get_by_category(self, svc):
        svc.create_template(_create_dto(name="A", category=TemplateCategory.BASIC.value))
        svc.create_template(_create_dto(name="B", category=TemplateCategory.CHAIN_OF_CUSTODY.value))
        results = svc.get_templates_by_category(TemplateCategory.BASIC.value)
        assert len(results) == 1
        assert results[0].name == "A"

    def test_get_by_tag(self, svc):
        svc.create_template(_create_dto(name="Tagged", tags=["forensics"]))
        svc.create_template(_create_dto(name="Untagged"))
        results = svc.get_templates_by_tag("forensics")
        assert len(results) == 1
        assert results[0].name == "Tagged"

    def test_get_recent_templates_ordered(self, svc):
        t1 = svc.create_template(_create_dto(name="Older", html_content="<p>{x}</p>"))
        t2 = svc.create_template(_create_dto(name="Newer", html_content="<p>{x}</p>"))
        # Render both to set last_used_at
        svc.render_template(t1.template_id, {"x": "a"})
        svc.render_template(t2.template_id, {"x": "b"})
        recents = svc.get_recent_templates(limit=5)
        assert len(recents) >= 1

    def test_search_templates(self, svc):
        svc.create_template(_create_dto(name="Alpha Report"))
        svc.create_template(_create_dto(name="Beta Form"))
        results = svc.search_templates("Alpha")
        assert len(results) == 1

    def test_get_top_used(self, svc):
        t = svc.create_template(_create_dto(html_content="<p>{x}</p>"))
        for _ in range(3):
            svc.render_template(t.template_id, {"x": "v"})
        top = svc.get_most_used_templates(limit=5)
        assert top[0].usage_count >= 3


# ===========================================================================
# Version history & rollback
# ===========================================================================

class TestVersionHistory:
    def test_initial_version_in_history(self, svc):
        created = svc.create_template(_create_dto())
        history = svc.get_version_history(created.template_id)
        assert len(history) >= 1
        assert history[0].version_number == 1

    def test_update_adds_version(self, svc):
        created = svc.create_template(_create_dto())
        svc.update_template(UpdateTemplateDto(template_id=created.template_id, html_content="<p>v2</p>", updated_by="bob"))
        history = svc.get_version_history(created.template_id)
        assert any(v.version_number == 2 for v in history)

    def test_get_template_version(self, svc):
        created = svc.create_template(_create_dto())
        v = svc.get_template_version(created.template_id, 1)
        assert v is not None
        assert v.version_number == 1

    def test_get_missing_version_returns_none(self, svc):
        created = svc.create_template(_create_dto())
        assert svc.get_template_version(created.template_id, 99) is None

    def test_rollback(self, svc, audit):
        created = svc.create_template(_create_dto(html_content="<p>v1</p>"))
        svc.update_template(UpdateTemplateDto(template_id=created.template_id, html_content="<p>v2</p>", updated_by="bob"))
        svc.rollback_to_version(created.template_id, 1, "alice")
        assert any(e["type"] == "TEMPLATE_ROLLED_BACK" for e in audit.events)


# ===========================================================================
# Statistics & usage tracking
# ===========================================================================

class TestStatistics:
    def test_record_usage(self, svc):
        created = svc.create_template(_create_dto())
        svc.record_usage(created.template_id)
        stats = svc.get_statistics(created.template_id)
        assert stats["usage_count"] >= 1

    def test_get_statistics_keys(self, svc):
        created = svc.create_template(_create_dto())
        stats = svc.get_statistics(created.template_id)
        for key in ("template_id", "name", "usage_count", "is_published"):
            assert key in stats

    def test_get_all_statistics(self, svc):
        svc.create_template(_create_dto(name="A"))
        svc.create_template(_create_dto(name="B"))
        all_stats = svc.get_all_statistics()
        assert len(all_stats) == 2


# ===========================================================================
# Favorites
# ===========================================================================

class TestFavorites:
    def test_add_to_favorites(self, svc):
        created = svc.create_template(_create_dto())
        svc.add_to_favorites(created.template_id, "alice")
        favs = svc.get_favorite_templates("alice")
        assert any(f.template_id == created.template_id for f in favs)

    def test_remove_from_favorites(self, svc):
        created = svc.create_template(_create_dto())
        svc.add_to_favorites(created.template_id, "alice")
        svc.remove_from_favorites(created.template_id, "alice")
        favs = svc.get_favorite_templates("alice")
        assert not any(f.template_id == created.template_id for f in favs)


# ===========================================================================
# Import / export
# ===========================================================================

class TestImportExport:
    def test_import_from_json(self, svc):
        data = {
            "name": "JSON Template",
            "category": TemplateCategory.BASIC.value,
            "html_content": "<p>From JSON</p>",
        }
        dto = svc.import_from_json(data, "alice")
        assert dto.name == "JSON Template"

    def test_export_to_json(self, svc):
        created = svc.create_template(_create_dto(name="ExportMe"))
        exported = svc.export_to_json(created.template_id)
        assert exported["name"] == "ExportMe"
        assert "html_content" in exported

    def test_export_to_html(self, svc):
        created = svc.create_template(_create_dto(html_content="<p>raw</p>"))
        html = svc.export_to_html(created.template_id)
        assert "<p>raw</p>" in html

    def test_import_from_html(self, svc):
        dto = svc.import_from_html("<p>Hello</p>", "HTML Import", "alice")
        assert dto.name == "HTML Import"

    def test_clone_template(self, svc, audit):
        original = svc.create_template(_create_dto(name="Original"))
        cloned = svc.clone_template(original.template_id, "Cloned", "alice")
        assert cloned.name == "Cloned"
        assert cloned.is_published is False
        assert any(e["type"] == "TEMPLATE_CLONED" for e in audit.events)

    def test_clone_empty_name_raises(self, svc):
        original = svc.create_template(_create_dto())
        with pytest.raises(DomainValidationError):
            svc.clone_template(original.template_id, "", "alice")


# ===========================================================================
# Seeding / backward-compat
# ===========================================================================

class TestSeeding:
    def test_get_or_create_basic(self, svc, monkeypatch):
        # Ensure templates.py DEFAULT_TEMPLATES is monkeypatched to avoid disk reads
        import templates as tpl_module
        monkeypatch.setattr(tpl_module, "DEFAULT_TEMPLATES", {
            "Basic Template": "<h1>Basic</h1>",
            "SWGDE/NIST Standard": "<h1>SWGDE</h1>",
        })
        dto = svc.get_or_create_basic_template()
        assert dto.name == "Basic Template"
        # Second call returns existing
        dto2 = svc.get_or_create_basic_template()
        assert dto2.template_id == dto.template_id

    def test_get_or_create_swgde_nist(self, svc, monkeypatch):
        import templates as tpl_module
        monkeypatch.setattr(tpl_module, "DEFAULT_TEMPLATES", {
            "SWGDE/NIST Standard": "<h1>SWGDE</h1>",
            "Basic Template": "<h1>Basic</h1>",
        })
        dto = svc.get_or_create_swgde_nist_template()
        assert dto.name == "SWGDE/NIST Standard"

    def test_initialize_default_templates_creates_both(self, svc, monkeypatch, tmp_path):
        import templates as tpl_module
        monkeypatch.setattr(tpl_module, "DEFAULT_TEMPLATES", {
            "Basic Template": "<h1>Basic</h1>",
            "SWGDE/NIST Standard": "<h1>SWGDE</h1>",
        })
        # Prevent templates.json load from disk
        monkeypatch.chdir(tmp_path)
        svc.initialize_default_templates()
        all_t = svc.get_all_templates()
        names = {t.name for t in all_t}
        assert "Basic Template" in names
        assert "SWGDE/NIST Standard" in names
