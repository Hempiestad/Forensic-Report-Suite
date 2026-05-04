"""tests/integration/test_sqlite_template_repository.py

SQLite Template repository: schema check, full CRUD, category/tags/flags
roundtrips, query methods (get_by_name, get_published, get_by_category,
search, record_usage, publish/unpublish), and UnitOfWork wiring.
All tests use isolated tmp_path databases.

NOTE: child-table (version_history, placeholders) persistence is already
covered in test_sqlite_template_versions.py — this file focuses on the
main templates table and query API.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from domain.entities.template import Template
from domain.entities.template_placeholder import PlaceholderType, TemplatePlaceholder
from domain.enums.template_category import TemplateCategory
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_template_repository import (
    SQLiteTemplateRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "tmpl.db"))


def _repo(tmp_path: Path) -> tuple[SQLiteDbContext, SQLiteTemplateRepository]:
    db = _ctx(tmp_path)
    return db, SQLiteTemplateRepository(db)


def _tmpl(
    id: int = 1,
    name: str = "Test Template",
    category: TemplateCategory = TemplateCategory.SWGDE_NIST,
    html: str = "<p>Hello {case_number}</p>",
    created_by: str = "alice",
) -> Template:
    return Template.create(
        id=id,
        name=name,
        category=category,
        html_content=html,
        created_by=created_by,
        description="A test template.",
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_templates_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='templates'"
        ).fetchone()
        assert row is not None

    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestSQLiteTemplateRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, name="My Report"))
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.name == "My Report"
        assert loaded.category == TemplateCategory.SWGDE_NIST

    def test_get_by_id_returns_none_for_missing(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_by_id("999") is None

    def test_get_all(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1))
        repo.add(_tmpl(2, name="Second"))
        db.commit()
        assert len(repo.get_all()) == 2

    def test_update_name_and_html(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        tmpl.name = "Updated Name"
        tmpl.html_content = "<p>New content</p>"
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.name == "Updated Name"
        assert loaded.html_content == "<p>New content</p>"

    def test_delete(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1))
        db.commit()
        repo.delete("1")
        db.commit()
        assert repo.get_by_id("1") is None

    def test_exists_true(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1))
        db.commit()
        assert repo.exists("1") is True

    def test_exists_false(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.exists("99") is False


# ---------------------------------------------------------------------------
# Field roundtrips
# ---------------------------------------------------------------------------

class TestFieldRoundtrips:
    def test_category_roundtrip_all_values(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        for i, cat in enumerate(TemplateCategory, start=1):
            t = _tmpl(i, name=f"T{i}", category=cat)
            repo.add(t)
        db.commit()
        loaded = repo.get_all()
        categories = {t.category for t in loaded}
        assert set(TemplateCategory) == categories

    def test_tags_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.tags = ["forensics", "mobile", "evidence"]
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.tags == ["forensics", "mobile", "evidence"]

    def test_tags_empty_list_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.tags = []
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.tags == []

    def test_is_published_false_by_default(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1))
        db.commit()
        assert repo.get_by_id("1").is_published is False

    def test_is_default_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.is_default = True
        repo.add(tmpl)
        db.commit()
        assert repo.get_by_id("1").is_default is True

    def test_is_favorite_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.is_favorite = True
        repo.add(tmpl)
        db.commit()
        assert repo.get_by_id("1").is_favorite is True

    def test_usage_count_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.usage_count = 42
        repo.add(tmpl)
        db.commit()
        assert repo.get_by_id("1").usage_count == 42

    def test_parent_template_id_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        # parent template must exist first
        repo.add(_tmpl(10, name="Parent"))
        tmpl = _tmpl(1)
        tmpl.parent_template_id = 10
        repo.add(tmpl)
        db.commit()
        assert repo.get_by_id("1").parent_template_id == 10

    def test_description_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.description = "Detailed description."
        repo.add(tmpl)
        db.commit()
        assert repo.get_by_id("1").description == "Detailed description."

    def test_created_by_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, created_by="charlie"))
        db.commit()
        assert repo.get_by_id("1").created_by == "charlie"

    def test_modified_by_persisted_via_update(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        tmpl.modified_by = "bob"
        repo.update(tmpl)
        db.commit()
        assert repo.get_by_id("1").modified_by == "bob"


# ---------------------------------------------------------------------------
# publish / unpublish lifecycle
# ---------------------------------------------------------------------------

class TestPublishLifecycle:
    def test_publish_sets_is_published(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        tmpl.publish("alice")
        repo.update(tmpl)
        db.commit()
        assert repo.get_by_id("1").is_published is True

    def test_unpublish_clears_is_published(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.publish("alice")
        repo.add(tmpl)
        db.commit()
        tmpl.unpublish("alice")
        repo.update(tmpl)
        db.commit()
        assert repo.get_by_id("1").is_published is False


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------

class TestRecordUsage:
    def test_record_usage_increments_count(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        tmpl.record_usage()
        repo.update(tmpl)
        db.commit()
        assert repo.get_by_id("1").usage_count == 1

    def test_record_usage_sets_last_used_at(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        tmpl.record_usage()
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.last_used_at is not None
        assert isinstance(loaded.last_used_at, datetime)

    def test_record_usage_multiple_times(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        for _ in range(3):
            tmpl.record_usage()
        repo.update(tmpl)
        db.commit()
        assert repo.get_by_id("1").usage_count == 3


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------

class TestQueryMethods:
    def test_get_by_name_found(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, name="Unique Name"))
        db.commit()
        found = repo.get_by_name("Unique Name")
        assert found is not None
        assert found.name == "Unique Name"

    def test_get_by_name_not_found(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_by_name("Does Not Exist") is None

    def test_get_published_returns_only_published(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        t1 = _tmpl(1, name="Published")
        t1.publish("alice")
        repo.add(t1)
        repo.add(_tmpl(2, name="Draft"))
        db.commit()
        published = repo.get_published()
        assert len(published) == 1
        assert published[0].name == "Published"

    def test_get_published_empty(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1))
        db.commit()
        assert repo.get_published() == []

    def test_get_by_category(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, category=TemplateCategory.SWGDE_NIST))
        repo.add(_tmpl(2, name="Mobile", category=TemplateCategory.MOBILE_DEVICE))
        repo.add(_tmpl(3, name="NIST 2", category=TemplateCategory.SWGDE_NIST))
        db.commit()
        result = repo.get_by_category(TemplateCategory.SWGDE_NIST.value)
        assert len(result) == 2
        assert all(t.category == TemplateCategory.SWGDE_NIST for t in result)

    def test_get_by_category_empty(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, category=TemplateCategory.SWGDE_NIST))
        db.commit()
        assert repo.get_by_category(TemplateCategory.MOBILE_DEVICE.value) == []

    def test_search_by_name(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, name="Mobile Forensics Report"))
        repo.add(_tmpl(2, name="Network Audit"))
        db.commit()
        results = repo.search("mobile")
        assert len(results) == 1
        assert results[0].name == "Mobile Forensics Report"

    def test_search_by_html_content(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, html="<p>Evidence hash: {hash}</p>"))
        repo.add(_tmpl(2, name="Other", html="<p>No special token</p>"))
        db.commit()
        results = repo.search("evidence hash")
        assert len(results) == 1
        assert results[0].id == 1

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1, name="SWGDE Report"))
        db.commit()
        assert len(repo.search("swgde")) == 1
        assert len(repo.search("SWGDE")) == 1

    def test_search_no_results(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_tmpl(1))
        db.commit()
        assert repo.search("zyxwvut") == []

    def test_search_matches_description(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.description = "Used for chain-of-custody documentation."
        repo.add(tmpl)
        db.commit()
        results = repo.search("chain-of-custody")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Delete removes child rows
# ---------------------------------------------------------------------------

class TestDeleteCascade:
    def test_delete_removes_version_rows(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        repo.add(tmpl)
        db.commit()
        # Verify version row exists
        assert db.connection.execute(
            "SELECT COUNT(*) FROM template_versions WHERE template_id=1"
        ).fetchone()[0] == 1
        repo.delete("1")
        db.commit()
        assert db.connection.execute(
            "SELECT COUNT(*) FROM template_versions WHERE template_id=1"
        ).fetchone()[0] == 0

    def test_delete_removes_placeholder_rows(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl(1)
        tmpl.add_placeholder(TemplatePlaceholder.string("case_number", "Case number"))
        repo.add(tmpl)
        db.commit()
        assert db.connection.execute(
            "SELECT COUNT(*) FROM template_placeholders WHERE template_id=1"
        ).fetchone()[0] == 1
        repo.delete("1")
        db.commit()
        assert db.connection.execute(
            "SELECT COUNT(*) FROM template_placeholders WHERE template_id=1"
        ).fetchone()[0] == 0


# ---------------------------------------------------------------------------
# _parse_category / _parse_tags static helpers
# ---------------------------------------------------------------------------

class TestStaticHelpers:
    def test_parse_category_all_values(self) -> None:
        for cat in TemplateCategory:
            assert SQLiteTemplateRepository._parse_category(cat.value) == cat

    def test_parse_category_unknown_falls_back(self) -> None:
        assert SQLiteTemplateRepository._parse_category("totally_unknown") == TemplateCategory.BASIC

    def test_parse_tags_from_json_string(self) -> None:
        raw = json.dumps(["a", "b"])
        assert SQLiteTemplateRepository._parse_tags(raw) == ["a", "b"]

    def test_parse_tags_from_list(self) -> None:
        assert SQLiteTemplateRepository._parse_tags(["x", "y"]) == ["x", "y"]

    def test_parse_tags_none_returns_empty(self) -> None:
        assert SQLiteTemplateRepository._parse_tags(None) == []

    def test_parse_tags_invalid_json_returns_empty(self) -> None:
        assert SQLiteTemplateRepository._parse_tags("not-json") == []

    def test_parse_ph_type_all_values(self) -> None:
        for ph_type in PlaceholderType:
            assert SQLiteTemplateRepository._parse_ph_type(ph_type.value) == ph_type

    def test_parse_ph_type_unknown_falls_back_to_string(self) -> None:
        assert SQLiteTemplateRepository._parse_ph_type("unknown") == PlaceholderType.STRING


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkTemplateWiring:
    def test_memory_provider(self) -> None:
        from infrastructure.persistence.repositories.template_repository import (
            InMemoryTemplateRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.templates, InMemoryTemplateRepository)

    def test_sqlite_provider(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow.db"))
        assert isinstance(uow.templates, SQLiteTemplateRepository)

    def test_sqlite_full_roundtrip_via_uow(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow2.db"))
        tmpl = _tmpl(1, name="UoW Template")
        uow.templates.add(tmpl)
        uow.commit()
        loaded = uow.templates.get_by_id("1")
        assert loaded is not None
        assert loaded.name == "UoW Template"
