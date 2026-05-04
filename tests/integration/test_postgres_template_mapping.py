"""tests/integration/test_postgres_template_mapping.py

PostgreSQL Template repository: static helper tests (_parse_category,
_parse_tags, _parse_ph_type), UnitOfWork provider selection, and live
CRUD tests gated by FORENSIC_PG_DSN.

NOTE: _to_entity requires a live DB connection (executes child-table
sub-queries), so it is covered only in the live test class. The static
helpers are tested independently without any DB connection.
"""
from __future__ import annotations

import os

import pytest

from domain.entities.template_placeholder import PlaceholderType
from domain.enums.template_category import TemplateCategory
from infrastructure.persistence.repositories.postgres_template_repository import (
    PostgreSQLTemplateRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


_skip_pg = pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")


# ---------------------------------------------------------------------------
# _parse_category static helper
# ---------------------------------------------------------------------------

class TestParseCategory:
    def test_all_valid_values(self) -> None:
        for cat in TemplateCategory:
            assert PostgreSQLTemplateRepository._parse_category(cat.value) == cat

    def test_unknown_falls_back_to_basic(self) -> None:
        assert PostgreSQLTemplateRepository._parse_category("totally_unknown") == TemplateCategory.BASIC

    def test_empty_string_falls_back_to_basic(self) -> None:
        assert PostgreSQLTemplateRepository._parse_category("") == TemplateCategory.BASIC


# ---------------------------------------------------------------------------
# _parse_tags static helper
# ---------------------------------------------------------------------------

class TestParseTags:
    def test_none_returns_empty_list(self) -> None:
        assert PostgreSQLTemplateRepository._parse_tags(None) == []

    def test_empty_string_returns_empty_list(self) -> None:
        assert PostgreSQLTemplateRepository._parse_tags("") == []

    def test_list_passthrough(self) -> None:
        assert PostgreSQLTemplateRepository._parse_tags(["forensics", "mobile"]) == ["forensics", "mobile"]

    def test_json_string_decoded(self) -> None:
        import json
        raw = json.dumps(["a", "b", "c"])
        assert PostgreSQLTemplateRepository._parse_tags(raw) == ["a", "b", "c"]

    def test_invalid_json_returns_empty_list(self) -> None:
        assert PostgreSQLTemplateRepository._parse_tags("not-json-at-all") == []

    def test_json_non_list_returns_empty_list(self) -> None:
        import json
        assert PostgreSQLTemplateRepository._parse_tags(json.dumps({"k": "v"})) == []

    def test_empty_list(self) -> None:
        assert PostgreSQLTemplateRepository._parse_tags([]) == []


# ---------------------------------------------------------------------------
# _parse_ph_type static helper
# ---------------------------------------------------------------------------

class TestParsePlaceholderType:
    def test_all_valid_values(self) -> None:
        for ph_type in PlaceholderType:
            assert PostgreSQLTemplateRepository._parse_ph_type(ph_type.value) == ph_type

    def test_unknown_falls_back_to_string(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("unknown_type") == PlaceholderType.STRING

    def test_empty_string_falls_back_to_string(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("") == PlaceholderType.STRING


# ---------------------------------------------------------------------------
# UnitOfWork provider selection
# ---------------------------------------------------------------------------

class TestUoWPostgresTemplateProviderSelection:
    def test_memory_provider_uses_inmemory(self) -> None:
        from infrastructure.persistence.repositories.template_repository import (
            InMemoryTemplateRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.templates, InMemoryTemplateRepository)

    def test_sqlite_provider_uses_sqlite(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.sqlite_template_repository import (
            SQLiteTemplateRepository,
        )
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "tmpl.db"))
        assert isinstance(uow.templates, SQLiteTemplateRepository)

    @_skip_pg
    def test_postgres_provider_uses_postgres(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.templates, PostgreSQLTemplateRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (gated by FORENSIC_PG_DSN)
# ---------------------------------------------------------------------------

@_skip_pg
class TestPostgresLiveTemplateCRUD:
    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_by_id(self) -> None:
        from domain.entities.template import Template
        uow = self._uow()
        tmpl = Template.create(
            id=99201,
            name="PG Template CRUD Test",
            category=TemplateCategory.SWGDE_NIST,
            html_content="<p>{case_number}</p>",
            created_by="pg_tester",
        )
        try:
            uow.templates.add(tmpl)
            uow.commit()
            loaded = uow.templates.get_by_id("99201")
            assert loaded is not None
            assert loaded.name == "PG Template CRUD Test"
            assert loaded.category == TemplateCategory.SWGDE_NIST
            assert loaded.created_by == "pg_tester"
        finally:
            uow.templates.delete("99201")
            uow.commit()

    def test_publish_and_get_published(self) -> None:
        from domain.entities.template import Template
        uow = self._uow()
        tmpl = Template.create(
            id=99202,
            name="PG Publish Test",
            category=TemplateCategory.MOBILE_DEVICE,
            html_content="<p>Mobile report</p>",
            created_by="pg_tester",
        )
        try:
            uow.templates.add(tmpl)
            uow.commit()
            tmpl.publish("pg_tester")
            uow.templates.update(tmpl)
            uow.commit()
            loaded = uow.templates.get_by_id("99202")
            assert loaded.is_published is True
        finally:
            uow.templates.delete("99202")
            uow.commit()

    def test_tags_roundtrip(self) -> None:
        from domain.entities.template import Template
        uow = self._uow()
        tmpl = Template.create(
            id=99203,
            name="PG Tags Test",
            category=TemplateCategory.CLOUD_FORENSICS,
            html_content="<p>Cloud</p>",
            created_by="pg_tester",
        )
        tmpl.tags = ["cloud", "evidence", "v2"]
        try:
            uow.templates.add(tmpl)
            uow.commit()
            loaded = uow.templates.get_by_id("99203")
            assert loaded.tags == ["cloud", "evidence", "v2"]
        finally:
            uow.templates.delete("99203")
            uow.commit()

    def test_version_history_and_placeholders(self) -> None:
        from domain.entities.template import Template
        from domain.entities.template_placeholder import TemplatePlaceholder
        uow = self._uow()
        tmpl = Template.create(
            id=99204,
            name="PG Child Tables Test",
            category=TemplateCategory.SWGDE_NIST,
            html_content="<p>{examiner}</p>",
            created_by="pg_tester",
        )
        tmpl.add_placeholder(TemplatePlaceholder.string("examiner", "Examiner name"))
        try:
            uow.templates.add(tmpl)
            uow.commit()
            tmpl.create_new_version("<p>v2 {examiner}</p>", changed_by="pg_tester", notes="v2")
            uow.templates.update(tmpl)
            uow.commit()
            loaded = uow.templates.get_by_id("99204")
            assert len(loaded.version_history) == 2
            assert len(loaded.placeholders) == 1
            assert loaded.placeholders[0].name == "examiner"
        finally:
            uow.templates.delete("99204")
            uow.commit()
