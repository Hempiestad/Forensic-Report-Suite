"""tests/integration/test_postgres_legal_process_mapping.py

PostgreSQL LegalProcess repository: mapping tests (no live DB required),
UnitOfWork provider selection. Live tests gated by FORENSIC_PG_DSN.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import pytest

from domain.entities.legal_process import LegalProcess
from infrastructure.persistence.repositories.postgres_legal_process_repository import (
    PostgreSQLLegalProcessRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


_skip_pg = pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")


def _row(**overrides) -> dict:
    base: dict = {
        "id": 1,
        "case_number": "LP-001",
        "process_type": "subpoena",
        "provider": "DA",
        "status": "pending",
        "submission_date": None,
        "due_date": None,
        "expiration_date": None,
        "received_date": None,
        "analysis_start_date": None,
        "completed_date": None,
        "investigator_approved": False,
        "investigator_approved_by": None,
        "investigator_approved_at": None,
        "state_attorney_approved": False,
        "state_attorney_approved_by": None,
        "state_attorney_approved_at": None,
        "judicial_approved": False,
        "judicial_approved_by": None,
        "judicial_approved_at": None,
        "notes": None,
        "ndr": False,
        "created_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _to_entity mapping (no live DB)
# ---------------------------------------------------------------------------

class TestPostgresLegalProcessMapping:
    def _repo(self) -> PostgreSQLLegalProcessRepository:
        return PostgreSQLLegalProcessRepository.__new__(PostgreSQLLegalProcessRepository)

    def test_basic_fields(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row())
        assert isinstance(lp, LegalProcess)
        assert lp.id == 1
        assert lp.case_number == "LP-001"
        assert lp.process_type == "subpoena"
        assert lp.provider == "DA"
        assert lp.status == "pending"

    def test_approvals_false_by_default(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row())
        assert lp.investigator_approved is False
        assert lp.state_attorney_approved is False
        assert lp.judicial_approved is False

    def test_investigator_approved_true(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 5, 1, tzinfo=timezone.utc)
        lp = repo._to_entity(_row(
            investigator_approved=True,
            investigator_approved_by="det-alice",
            investigator_approved_at=ts,
        ))
        assert lp.investigator_approved is True
        assert lp.investigator_approved_by == "det-alice"
        assert lp.investigator_approved_at == ts

    def test_state_attorney_approved_true(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(
            state_attorney_approved=True,
            state_attorney_approved_by="atty-bob",
            state_attorney_approved_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        ))
        assert lp.state_attorney_approved is True
        assert lp.state_attorney_approved_by == "atty-bob"

    def test_judicial_approved_true(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(
            judicial_approved=True,
            judicial_approved_by="judge-carol",
            judicial_approved_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        ))
        assert lp.judicial_approved is True
        assert lp.judicial_approved_by == "judge-carol"

    def test_all_date_fields_passthrough(self) -> None:
        repo = self._repo()
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        lp = repo._to_entity(_row(
            submission_date=now,
            due_date=now + timedelta(days=30),
            expiration_date=now + timedelta(days=60),
            received_date=now + timedelta(days=1),
            analysis_start_date=now + timedelta(days=2),
            completed_date=now + timedelta(days=45),
        ))
        assert lp.submission_date == now
        assert lp.due_date == now + timedelta(days=30)
        assert lp.expiration_date == now + timedelta(days=60)
        assert lp.received_date == now + timedelta(days=1)
        assert lp.analysis_start_date == now + timedelta(days=2)
        assert lp.completed_date == now + timedelta(days=45)

    def test_all_optional_dates_none(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row())
        assert lp.submission_date is None
        assert lp.due_date is None
        assert lp.expiration_date is None
        assert lp.received_date is None
        assert lp.analysis_start_date is None
        assert lp.completed_date is None

    def test_ndr_false(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(ndr=False))
        assert lp.ndr is False

    def test_ndr_true(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(ndr=True))
        assert lp.ndr is True

    def test_notes_persist(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(notes="Some process notes."))
        assert lp.notes == "Some process notes."

    def test_notes_none(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(notes=None))
        assert lp.notes is None

    def test_created_at_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        lp = repo._to_entity(_row(created_at=ts))
        assert lp.created_at == ts

    def test_created_at_none_fallback(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(created_at=None))
        assert isinstance(lp.created_at, datetime)

    def test_provider_none(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(provider=None))
        assert lp.provider is None

    def test_status_values(self) -> None:
        repo = self._repo()
        for status in ["pending", "sent", "acknowledged", "completed", "cancelled"]:
            lp = repo._to_entity(_row(status=status))
            assert lp.status == status

    def test_process_type_values(self) -> None:
        repo = self._repo()
        for pt in ["subpoena", "search_warrant", "court_order"]:
            lp = repo._to_entity(_row(process_type=pt))
            assert lp.process_type == pt

    def test_id_coercion(self) -> None:
        repo = self._repo()
        lp = repo._to_entity(_row(id=77))
        assert lp.id == 77
        assert isinstance(lp.id, int)


# ---------------------------------------------------------------------------
# UnitOfWork provider selection
# ---------------------------------------------------------------------------

class TestUoWPostgresLegalProcessProviderSelection:
    def test_memory_provider_uses_inmemory(self) -> None:
        from infrastructure.persistence.repositories.legal_process_repository import (
            InMemoryLegalProcessRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.legal_processes, InMemoryLegalProcessRepository)

    def test_sqlite_provider_uses_sqlite(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.sqlite_legal_process_repository import (
            SQLiteLegalProcessRepository,
        )
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "lp.db"))
        assert isinstance(uow.legal_processes, SQLiteLegalProcessRepository)

    @_skip_pg
    def test_postgres_provider_uses_postgres(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.legal_processes, PostgreSQLLegalProcessRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (gated by FORENSIC_PG_DSN)
# ---------------------------------------------------------------------------

@_skip_pg
class TestPostgresLiveLegalProcessCRUD:
    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_by_id(self) -> None:
        uow = self._uow()
        lp = LegalProcess(
            id=99101,
            case_number="PG-LP-001",
            process_type="subpoena",
            provider="DA",
            status="pending",
            notes="PG integration test.",
        )
        try:
            uow.legal_processes.add(lp)
            uow.commit()
            loaded = uow.legal_processes.get_by_id("99101")
            assert loaded is not None
            assert loaded.case_number == "PG-LP-001"
            assert loaded.provider == "DA"
        finally:
            uow.legal_processes.delete("99101")
            uow.commit()

    def test_approval_workflow(self) -> None:
        uow = self._uow()
        lp = LegalProcess(
            id=99102,
            case_number="PG-LP-002",
            process_type="search_warrant",
            status="pending",
        )
        try:
            uow.legal_processes.add(lp)
            uow.commit()

            lp.approve_investigator("pg-inv")
            lp.approve_state_attorney("pg-atty")
            lp.approve_judicial("pg-judge")
            uow.legal_processes.update(lp)
            uow.commit()

            loaded = uow.legal_processes.get_by_id("99102")
            assert loaded.is_fully_approved is True
            assert loaded.investigator_approved_by == "pg-inv"
        finally:
            uow.legal_processes.delete("99102")
            uow.commit()
