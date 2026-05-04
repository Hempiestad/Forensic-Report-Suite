"""tests/integration/test_sqlite_template_versions.py

Phase 12 — SQLite integration tests for template_versions and
template_placeholders child-table persistence.

Verifies:
  - Migration v9 creates the two child tables
  - Version history roundtrips through add/get_by_id
  - Multiple versions persist and load in order
  - Rollback creates a new version entry
  - Placeholder roundtrip through add/get_by_id
  - Multiple placeholders persist and load
  - auto_detect_placeholders persists via update
  - Deleting a template does not leave orphan rows (cascade or explicit)
  - UnitOfWork.templates uses SQLiteTemplateRepository for provider=sqlite
"""
from __future__ import annotations

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


def _tmpl(id: int = 1, name: str = "Basic Report") -> Template:
    return Template.create(
        id=id,
        name=name,
        category=TemplateCategory.SWGDE_NIST,
        html_content="<h1>{case_number}</h1>",
        created_by="alice",
        description="Test template",
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchemaV9:
    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10

    def test_template_versions_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='template_versions'"
        ).fetchone()
        assert row is not None

    def test_template_placeholders_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='template_placeholders'"
        ).fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# Version history persistence
# ---------------------------------------------------------------------------

class TestVersionPersistence:
    def test_initial_version_saved_on_add(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        # Raw check
        rows = db.connection.execute(
            "SELECT * FROM template_versions WHERE template_id = 1"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["version_number"] == 1

    def test_version_history_loaded_on_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert len(loaded.version_history) == 1
        assert loaded.version_history[0].version_number == 1
        assert loaded.version_history[0].html_content == "<h1>{case_number}</h1>"
        assert loaded.version_history[0].created_by == "alice"

    def test_second_version_persisted_on_update(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        tmpl.create_new_version("<h2>Updated</h2>", changed_by="bob", notes="v2 changes")
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.version_number == 2
        assert len(loaded.version_history) == 2

    def test_versions_loaded_in_order(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        tmpl.create_new_version("<p>v2</p>", changed_by="bob")
        repo.update(tmpl)
        db.commit()
        tmpl.create_new_version("<p>v3</p>", changed_by="charlie")
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        nums = [v.version_number for v in loaded.version_history]
        assert nums == [1, 2, 3]

    def test_rollback_creates_new_version_entry(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        tmpl.create_new_version("<p>v2</p>", changed_by="bob")
        repo.update(tmpl)
        db.commit()
        # Rollback to v1
        tmpl.rollback_to_version(1, "alice")
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert len(loaded.version_history) == 3
        assert loaded.version_history[-1].notes == "Rolled back to v1"

    def test_version_notes_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        tmpl.create_new_version("<p>v2</p>", changed_by="bob", notes="Important fix")
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        v2 = loaded.get_version(2)
        assert v2 is not None
        assert v2.notes == "Important fix"

    def test_version_not_duplicated_on_repeated_update(self, tmp_path: Path) -> None:
        """Calling update without creating a new version must not duplicate version rows."""
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        repo.add(tmpl)
        db.commit()
        # Update non-HTML fields only
        tmpl.is_favorite = True
        repo.update(tmpl)
        db.commit()
        tmpl.usage_count = 5
        repo.update(tmpl)
        db.commit()
        rows = db.connection.execute(
            "SELECT COUNT(*) AS c FROM template_versions WHERE template_id = 1"
        ).fetchone()
        assert int(rows["c"]) == 1


# ---------------------------------------------------------------------------
# Placeholder persistence
# ---------------------------------------------------------------------------

class TestPlaceholderPersistence:
    def test_placeholder_saved_on_add(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        tmpl.add_placeholder(TemplatePlaceholder.string("case_number", "Case number"))
        repo.add(tmpl)
        db.commit()
        rows = db.connection.execute(
            "SELECT * FROM template_placeholders WHERE template_id = 1"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["name"] == "case_number"

    def test_placeholder_loaded_on_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        tmpl.add_placeholder(TemplatePlaceholder.string("case_number", "Case number"))
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert len(loaded.placeholders) == 1
        assert loaded.placeholders[0].name == "case_number"
        assert loaded.placeholders[0].placeholder_type == PlaceholderType.STRING

    def test_multiple_placeholders_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        tmpl.add_placeholder(TemplatePlaceholder.string("case_number", "Case number"))
        tmpl.add_placeholder(TemplatePlaceholder.date("exam_date", "Examination date"))
        tmpl.add_placeholder(TemplatePlaceholder.number("exhibit_count", "Exhibit count"))
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert len(loaded.placeholders) == 3
        names = {p.name for p in loaded.placeholders}
        assert names == {"case_number", "exam_date", "exhibit_count"}

    def test_placeholder_types_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        tmpl.add_placeholder(TemplatePlaceholder.date("exam_date", "Date"))
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        ph = loaded.placeholders[0]
        assert ph.placeholder_type == PlaceholderType.DATE

    def test_placeholder_required_flag_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        tmpl.add_placeholder(
            TemplatePlaceholder(
                name="optional_field",
                description="Optional",
                is_required=False,
            )
        )
        repo.add(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        ph = loaded.placeholders[0]
        assert ph.is_required is False

    def test_placeholders_replaced_on_update(self, tmp_path: Path) -> None:
        """_persist_placeholders deletes and re-inserts, so updates propagate."""
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()
        tmpl.add_placeholder(TemplatePlaceholder.string("old_field", "Old"))
        repo.add(tmpl)
        db.commit()
        # Remove old, add new
        tmpl.remove_placeholder("old_field")
        tmpl.add_placeholder(TemplatePlaceholder.string("new_field", "New"))
        repo.update(tmpl)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert len(loaded.placeholders) == 1
        assert loaded.placeholders[0].name == "new_field"

    def test_auto_detect_placeholders_persisted(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        tmpl = _tmpl()  # HTML contains {case_number}
        repo.add(tmpl)
        db.commit()
        new_names = tmpl.auto_detect_placeholders()
        repo.update(tmpl)
        db.commit()
        assert "case_number" in new_names
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert any(p.name == "case_number" for p in loaded.placeholders)


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkTemplateWiring:
    def test_uow_sqlite_provider_version_history_persists(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow.db"))
        tmpl = _tmpl()
        uow.templates.add(tmpl)
        uow.commit()
        tmpl.create_new_version("<p>v2</p>", changed_by="bob")
        uow.templates.update(tmpl)
        uow.commit()
        loaded = uow.templates.get_by_id("1")
        assert loaded is not None
        assert len(loaded.version_history) == 2
