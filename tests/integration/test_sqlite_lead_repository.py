"""tests/integration/test_sqlite_lead_repository.py

Integration tests for Phase 11 — SQLiteInvestigativeLeadRepository.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from domain.entities.investigative_lead import InvestigativeLead
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_lead_repository import (
    SQLiteInvestigativeLeadRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "test.db"))


def _repo(tmp_path: Path) -> tuple[SQLiteDbContext, SQLiteInvestigativeLeadRepository]:
    db = _ctx(tmp_path)
    return db, SQLiteInvestigativeLeadRepository(db)


_NOW = datetime(2025, 6, 1, 12, 0, 0)


def _lead(id: int = 1, case: str = "C-001", name: str = "Suspect Vehicle") -> InvestigativeLead:
    lead = InvestigativeLead.create(id=id, case_number=case, name=name)
    lead.created_at = _NOW
    lead.modified_at = _NOW
    return lead


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------

class TestSchemaV9:
    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10

    def test_investigative_leads_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='investigative_leads'"
        ).fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestSQLiteLeadCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        lead = _lead()
        repo.add(lead)
        db.commit()
        retrieved = repo.get_by_id("1")
        assert retrieved is not None
        assert retrieved.name == "Suspect Vehicle"
        assert retrieved.case_number == "C-001"

    def test_get_by_id_returns_none_for_missing(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_by_id("999") is None

    def test_get_all_returns_all_leads(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_lead(id=1, name="Lead A"))
        repo.add(_lead(id=2, name="Lead B"))
        db.commit()
        all_leads = repo.get_all()
        assert len(all_leads) == 2

    def test_update_persists_changes(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        lead = _lead()
        repo.add(lead)
        db.commit()
        lead.name = "Updated Name"
        lead.source = "Informant"
        repo.update(lead)
        db.commit()
        retrieved = repo.get_by_id("1")
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.source == "Informant"

    def test_delete_removes_lead(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_lead())
        db.commit()
        repo.delete("1")
        db.commit()
        assert repo.get_by_id("1") is None

    def test_exists_returns_true_for_present(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_lead())
        db.commit()
        assert repo.exists("1") is True

    def test_exists_returns_false_for_absent(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.exists("999") is False


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------

class TestSQLiteLeadQueries:
    def test_get_for_case_filters_correctly(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_lead(id=1, case="C-001"))
        repo.add(_lead(id=2, case="C-001"))
        repo.add(_lead(id=3, case="C-002"))
        db.commit()
        leads = repo.get_for_case("C-001")
        assert len(leads) == 2
        assert all(l.case_number == "C-001" for l in leads)

    def test_get_for_case_returns_empty_for_no_match(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_for_case("NOPE") == []

    def test_get_open_for_case_excludes_completed(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        open_lead = _lead(id=1, name="Open")
        closed_lead = _lead(id=2, name="Closed")
        closed_lead.mark_completed("bob")
        repo.add(open_lead)
        repo.add(closed_lead)
        db.commit()
        open_leads = repo.get_open_for_case("C-001")
        assert len(open_leads) == 1
        assert open_leads[0].name == "Open"

    def test_get_open_for_case_empty_when_all_complete(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        lead = _lead()
        lead.mark_completed("bob")
        repo.add(lead)
        db.commit()
        assert repo.get_open_for_case("C-001") == []


# ---------------------------------------------------------------------------
# Roundtrip mapping
# ---------------------------------------------------------------------------

class TestSQLiteLeadRoundtrip:
    def test_completed_lead_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        lead = _lead()
        lead.mark_completed("detective_jane")
        repo.add(lead)
        db.commit()
        retrieved = repo.get_by_id("1")
        assert retrieved is not None
        assert retrieved.completed is True
        assert retrieved.completed_by == "detective_jane"
        assert retrieved.completed_at is not None

    def test_optional_fields_none_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        lead = _lead()
        assert lead.source is None
        assert lead.description is None
        repo.add(lead)
        db.commit()
        retrieved = repo.get_by_id("1")
        assert retrieved is not None
        assert retrieved.source is None
        assert retrieved.description is None

    def test_all_fields_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        lead = InvestigativeLead(
            id=42,
            case_number="C-99",
            name="Full Lead",
            source="CCTV",
            description="Detailed description",
            completed=False,
            completed_at=None,
            completed_by=None,
            created_at=_NOW,
            modified_at=_NOW,
        )
        repo.add(lead)
        db.commit()
        retrieved = repo.get_by_id("42")
        assert retrieved is not None
        assert retrieved.id == 42
        assert retrieved.name == "Full Lead"
        assert retrieved.source == "CCTV"
        assert retrieved.description == "Detailed description"
        assert retrieved.created_at == _NOW


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkLeadsWiring:
    def test_uow_memory_provider_has_leads(self) -> None:
        from infrastructure.persistence.repositories.lead_repository import (
            InMemoryInvestigativeLeadRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.leads, InMemoryInvestigativeLeadRepository)

    def test_uow_sqlite_provider_has_sqlite_leads(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "wiring.db"))
        assert isinstance(uow.leads, SQLiteInvestigativeLeadRepository)

    def test_uow_custom_lead_repo_override(self) -> None:
        custom = SQLiteInvestigativeLeadRepository(_ctx(Path(".")))  # just for type check
        # Override via lead_repo kwarg — use memory provider to avoid creating files
        from infrastructure.persistence.repositories.lead_repository import (
            InMemoryInvestigativeLeadRepository,
        )
        override = InMemoryInvestigativeLeadRepository()
        uow = UnitOfWork(provider="memory", lead_repo=override)
        assert uow.leads is override
