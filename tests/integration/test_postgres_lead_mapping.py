"""tests/integration/test_postgres_lead_mapping.py

Phase 11 — PostgreSQL InvestigativeLead repository mapping + UnitOfWork tests.

Mapping tests exercise `_to_entity` logic without a live DB.
Live-DB tests are gated by the FORENSIC_PG_DSN environment variable.
"""
from __future__ import annotations

import os
from datetime import datetime

import pytest

from domain.entities.investigative_lead import InvestigativeLead
from infrastructure.persistence.repositories.postgres_lead_repository import (
    PostgreSQLInvestigativeLeadRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FORENSIC_PG_DSN = os.getenv("FORENSIC_PG_DSN")
_skip_pg = pytest.mark.skipif(not _FORENSIC_PG_DSN, reason="FORENSIC_PG_DSN not set")

_NOW = datetime(2025, 6, 1, 12, 0, 0)


def _lead_row(**overrides) -> dict:
    """Minimal lead row as PostgreSQL would return (via psycopg3 dict_row)."""
    base: dict = {
        "id": 1,
        "case_number": "C-001",
        "name": "Suspect Vehicle",
        "source": None,
        "description": None,
        "completed": False,
        "completed_at": None,
        "completed_by": None,
        "created_at": _NOW,
        "modified_at": _NOW,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _to_entity mapping (no live DB)
# ---------------------------------------------------------------------------

class TestPostgresLeadMapping:
    """Unit-test _to_entity mapping in isolation — no DB connection required."""

    def _mapper(self) -> PostgreSQLInvestigativeLeadRepository:
        """Return repo without a live connection (methods requiring it are not called)."""
        # Pass None; only _to_entity is exercised here
        return PostgreSQLInvestigativeLeadRepository.__new__(  # type: ignore[arg-type]
            PostgreSQLInvestigativeLeadRepository
        )

    def test_basic_row_maps_to_entity(self) -> None:
        repo = self._mapper()
        entity = repo._to_entity(_lead_row())
        assert isinstance(entity, InvestigativeLead)
        assert entity.id == 1
        assert entity.case_number == "C-001"
        assert entity.name == "Suspect Vehicle"

    def test_optional_fields_none(self) -> None:
        repo = self._mapper()
        entity = repo._to_entity(_lead_row(source=None, description=None))
        assert entity.source is None
        assert entity.description is None

    def test_all_optional_fields_present(self) -> None:
        repo = self._mapper()
        entity = repo._to_entity(
            _lead_row(source="CCTV", description="Footage from 5th Ave")
        )
        assert entity.source == "CCTV"
        assert entity.description == "Footage from 5th Ave"

    def test_completed_lead_maps_correctly(self) -> None:
        completed_at = datetime(2025, 6, 5, 9, 0, 0)
        repo = self._mapper()
        entity = repo._to_entity(
            _lead_row(completed=True, completed_at=completed_at, completed_by="detective_bob")
        )
        assert entity.completed is True
        assert entity.completed_at == completed_at
        assert entity.completed_by == "detective_bob"

    def test_open_lead_completed_fields_none(self) -> None:
        repo = self._mapper()
        entity = repo._to_entity(_lead_row(completed=False, completed_at=None, completed_by=None))
        assert entity.completed is False
        assert entity.completed_at is None
        assert entity.completed_by is None

    def test_iso_string_datetimes_are_parsed(self) -> None:
        repo = self._mapper()
        entity = repo._to_entity(
            _lead_row(
                created_at="2025-06-01T12:00:00",
                modified_at="2025-06-02T08:30:00",
            )
        )
        assert entity.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert entity.modified_at == datetime(2025, 6, 2, 8, 30, 0)

    def test_id_is_integer(self) -> None:
        repo = self._mapper()
        entity = repo._to_entity(_lead_row(id=99))
        assert entity.id == 99
        assert isinstance(entity.id, int)


# ---------------------------------------------------------------------------
# _parse_dt helper
# ---------------------------------------------------------------------------

class TestParseDt:
    def _mapper(self) -> PostgreSQLInvestigativeLeadRepository:
        return PostgreSQLInvestigativeLeadRepository.__new__(  # type: ignore[arg-type]
            PostgreSQLInvestigativeLeadRepository
        )

    def test_none_returns_none(self) -> None:
        assert self._mapper()._parse_dt(None) is None

    def test_datetime_passthrough(self) -> None:
        dt = datetime(2025, 1, 15, 8, 0)
        assert self._mapper()._parse_dt(dt) == dt

    def test_iso_string_parsed(self) -> None:
        result = self._mapper()._parse_dt("2025-06-01T12:00:00")
        assert result == datetime(2025, 6, 1, 12, 0, 0)

    def test_invalid_string_returns_none(self) -> None:
        assert self._mapper()._parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# UnitOfWork provider dispatch
# ---------------------------------------------------------------------------

class TestUnitOfWorkLeadsProviderDispatch:
    def test_memory_provider_uses_inmemory_repo(self) -> None:
        from infrastructure.persistence.repositories.lead_repository import (
            InMemoryInvestigativeLeadRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.leads, InMemoryInvestigativeLeadRepository)

    def test_postgres_provider_dispatches_to_postgres_repo(self) -> None:
        """Verify UnitOfWork selects PostgreSQLInvestigativeLeadRepository for postgres provider."""
        pytest.importorskip("psycopg2", reason="psycopg2 not installed")
        if not _FORENSIC_PG_DSN:
            pytest.skip("FORENSIC_PG_DSN not set — cannot create a PostgreSQL context")
        uow = UnitOfWork(provider="postgres", postgres_dsn=_FORENSIC_PG_DSN)
        assert isinstance(uow.leads, PostgreSQLInvestigativeLeadRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (gated)
# ---------------------------------------------------------------------------

@_skip_pg
class TestPostgresLeadRepositoryLive:
    def test_add_and_get_by_id(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_FORENSIC_PG_DSN)
        lead = InvestigativeLead.create(id=9001, case_number="PG-LEAD-001", name="PG Lead")
        uow.leads.add(lead)
        uow.commit()
        try:
            retrieved = uow.leads.get_by_id("9001")
            assert retrieved is not None
            assert retrieved.name == "PG Lead"
        finally:
            uow.leads.delete("9001")
            uow.commit()

    def test_get_for_case(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_FORENSIC_PG_DSN)
        l1 = InvestigativeLead.create(id=9002, case_number="PG-CASE-X", name="Lead 1")
        l2 = InvestigativeLead.create(id=9003, case_number="PG-CASE-X", name="Lead 2")
        uow.leads.add(l1)
        uow.leads.add(l2)
        uow.commit()
        try:
            leads = uow.leads.get_for_case("PG-CASE-X")
            assert len(leads) >= 2
        finally:
            uow.leads.delete("9002")
            uow.leads.delete("9003")
            uow.commit()
