"""tests/integration/test_postgres_template_version_mapping.py

Phase 12 — PostgreSQL template repository: mapping tests for
_parse_ph_type helper, _to_entity child-table structure, and UoW wiring.

Mapping tests that don't need a live DB exercise static helpers only.
Tests requiring a live PostgreSQL connection are gated by FORENSIC_PG_DSN.
"""
from __future__ import annotations

import os

import pytest

from domain.entities.template_placeholder import PlaceholderType
from infrastructure.persistence.repositories.postgres_template_repository import (
    PostgreSQLTemplateRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FORENSIC_PG_DSN = os.getenv("FORENSIC_PG_DSN")
_skip_pg = pytest.mark.skipif(not _FORENSIC_PG_DSN, reason="FORENSIC_PG_DSN not set")


def _repo() -> PostgreSQLTemplateRepository:
    """Return repo without a live connection — only static/helper methods tested."""
    return PostgreSQLTemplateRepository.__new__(  # type: ignore[arg-type]
        PostgreSQLTemplateRepository
    )


# ---------------------------------------------------------------------------
# _parse_ph_type static helper
# ---------------------------------------------------------------------------

class TestParsePlaceholderType:
    def test_string_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("string") == PlaceholderType.STRING

    def test_date_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("date") == PlaceholderType.DATE

    def test_number_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("number") == PlaceholderType.NUMBER

    def test_currency_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("currency") == PlaceholderType.CURRENCY

    def test_email_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("email") == PlaceholderType.EMAIL

    def test_phone_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("phone") == PlaceholderType.PHONE

    def test_url_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("url") == PlaceholderType.URL

    def test_reference_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("reference") == PlaceholderType.REFERENCE

    def test_boolean_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("boolean") == PlaceholderType.BOOLEAN

    def test_html_value(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("html") == PlaceholderType.HTML

    def test_unknown_falls_back_to_string(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("totally_unknown") == PlaceholderType.STRING

    def test_empty_string_falls_back_to_string(self) -> None:
        assert PostgreSQLTemplateRepository._parse_ph_type("") == PlaceholderType.STRING


# ---------------------------------------------------------------------------
# Method presence (structural)
# ---------------------------------------------------------------------------

class TestPostgresTemplateRepoStructure:
    def test_persist_versions_method_exists(self) -> None:
        assert hasattr(PostgreSQLTemplateRepository, "_persist_versions")
        assert callable(PostgreSQLTemplateRepository._persist_versions)

    def test_persist_placeholders_method_exists(self) -> None:
        assert hasattr(PostgreSQLTemplateRepository, "_persist_placeholders")
        assert callable(PostgreSQLTemplateRepository._persist_placeholders)

    def test_parse_ph_type_is_static(self) -> None:
        # Should be callable on the class without an instance
        result = PostgreSQLTemplateRepository._parse_ph_type("date")
        assert result == PlaceholderType.DATE

    def test_to_entity_method_exists(self) -> None:
        assert hasattr(PostgreSQLTemplateRepository, "_to_entity")
        assert callable(PostgreSQLTemplateRepository._to_entity)


# ---------------------------------------------------------------------------
# UnitOfWork dispatch — postgres provider
# ---------------------------------------------------------------------------

class TestUoWPostgresTemplateDispatch:
    @_skip_pg
    def test_uow_postgres_templates_is_postgres_repo(self) -> None:
        uow = UnitOfWork(provider="postgres", db_dsn=_FORENSIC_PG_DSN)
        assert isinstance(uow.templates, PostgreSQLTemplateRepository)


# ---------------------------------------------------------------------------
# Live-DB tests — all gated by FORENSIC_PG_DSN
# ---------------------------------------------------------------------------

class TestPostgresTemplateLive:
    @_skip_pg
    def test_add_and_reload_version_history(self) -> None:
        from domain.entities.template import Template
        from domain.enums.template_category import TemplateCategory

        uow = UnitOfWork(provider="postgres", db_dsn=_FORENSIC_PG_DSN)
        tmpl = Template.create(
            id=90001,
            name="PG Integration V12 Template",
            category=TemplateCategory.SWGDE_NIST,
            html_content="<p>{case_number}</p>",
            created_by="tester",
        )
        try:
            uow.templates.add(tmpl)
            uow.commit()
            tmpl.create_new_version("<p>v2</p>", changed_by="tester", notes="phase12")
            uow.templates.update(tmpl)
            uow.commit()
            loaded = uow.templates.get_by_id("90001")
            assert loaded is not None
            assert len(loaded.version_history) == 2
        finally:
            uow.templates.delete("90001")
            uow.commit()

    @_skip_pg
    def test_add_and_reload_placeholders(self) -> None:
        from domain.entities.template import Template
        from domain.entities.template_placeholder import TemplatePlaceholder
        from domain.enums.template_category import TemplateCategory

        uow = UnitOfWork(provider="postgres", db_dsn=_FORENSIC_PG_DSN)
        tmpl = Template.create(
            id=90002,
            name="PG Placeholder V12 Template",
            category=TemplateCategory.SWGDE_NIST,
            html_content="<p>{examiner}</p>",
            created_by="tester",
        )
        try:
            tmpl.add_placeholder(TemplatePlaceholder.string("examiner", "Examiner name"))
            uow.templates.add(tmpl)
            uow.commit()
            loaded = uow.templates.get_by_id("90002")
            assert loaded is not None
            assert len(loaded.placeholders) == 1
            assert loaded.placeholders[0].name == "examiner"
            assert loaded.placeholders[0].placeholder_type == PlaceholderType.STRING
        finally:
            uow.templates.delete("90002")
            uow.commit()
