"""tests/integration/test_sqlite_legal_process_repository.py

SQLite LegalProcess repository: schema check, full CRUD, approval workflow
roundtrip, SLA queries (get_overdue, get_due_soon), UnitOfWork wiring.
All tests use isolated tmp_path databases.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from domain.entities.legal_process import LegalProcess
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_legal_process_repository import (
    SQLiteLegalProcessRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _ctx(tmp_path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "lp.db"))


def _lp(
    id: int,
    case_number: str = "LP-001",
    process_type: str = "subpoena",
    status: str = "pending",
    due_days: int | None = None,
) -> LegalProcess:
    lp = LegalProcess(
        id=id,
        case_number=case_number,
        process_type=process_type,
        status=status,
    )
    if due_days is not None:
        lp.due_date = datetime.utcnow() + timedelta(days=due_days)
    return lp


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_legal_processes_table_exists(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        row = ctx.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='legal_processes'"
        ).fetchone()
        assert row is not None

    def test_schema_version(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        row = ctx.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestSQLiteLegalProcessRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = LegalProcess(
            id=1,
            case_number="LP-CRUD-001",
            process_type="subpoena",
            provider="DA",
            status="pending",
            notes="Initial subpoena.",
        )
        repo.add(lp)
        ctx.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.case_number == "LP-CRUD-001"
        assert loaded.provider == "DA"
        assert loaded.notes == "Initial subpoena."

    def test_get_by_id_returns_none_for_missing(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        assert repo.get_by_id("999") is None

    def test_get_all(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(1))
        repo.add(_lp(2))
        ctx.commit()
        all_items = repo.get_all()
        assert len(all_items) == 2

    def test_update_status_and_notes(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = _lp(10, status="pending")
        repo.add(lp)
        ctx.commit()

        lp.status = "sent"
        lp.notes = "Sent via courier."
        repo.update(lp)
        ctx.commit()

        reloaded = repo.get_by_id("10")
        assert reloaded.status == "sent"
        assert reloaded.notes == "Sent via courier."

    def test_delete(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(5))
        ctx.commit()
        repo.delete("5")
        ctx.commit()
        assert repo.get_by_id("5") is None

    def test_exists_true(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(7))
        ctx.commit()
        assert repo.exists("7") is True

    def test_exists_false(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        assert repo.exists("99") is False


# ---------------------------------------------------------------------------
# Approval workflow roundtrips
# ---------------------------------------------------------------------------

class TestApprovalWorkflowRoundtrip:
    def test_investigator_approval_persisted(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = _lp(20)
        repo.add(lp)
        ctx.commit()

        lp.approve_investigator("det-alice")
        repo.update(lp)
        ctx.commit()

        loaded = repo.get_by_id("20")
        assert loaded.investigator_approved is True
        assert loaded.investigator_approved_by == "det-alice"
        assert loaded.investigator_approved_at is not None

    def test_state_attorney_approval_persisted(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = _lp(21)
        repo.add(lp)
        ctx.commit()

        lp.approve_state_attorney("atty-bob")
        repo.update(lp)
        ctx.commit()

        loaded = repo.get_by_id("21")
        assert loaded.state_attorney_approved is True
        assert loaded.state_attorney_approved_by == "atty-bob"

    def test_judicial_approval_persisted(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = _lp(22)
        repo.add(lp)
        ctx.commit()

        lp.approve_judicial("judge-carol")
        repo.update(lp)
        ctx.commit()

        loaded = repo.get_by_id("22")
        assert loaded.judicial_approved is True
        assert loaded.judicial_approved_by == "judge-carol"

    def test_full_approval_chain(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = _lp(23)
        repo.add(lp)
        ctx.commit()

        lp.approve_investigator("inv")
        lp.approve_state_attorney("atty")
        lp.approve_judicial("judge")
        repo.update(lp)
        ctx.commit()

        loaded = repo.get_by_id("23")
        assert loaded.is_fully_approved is True

    def test_approvals_default_false(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(24))
        ctx.commit()
        loaded = repo.get_by_id("24")
        assert loaded.investigator_approved is False
        assert loaded.state_attorney_approved is False
        assert loaded.judicial_approved is False


# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------

class TestStatusLifecycle:
    def test_status_lifecycle_persists(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = _lp(30, status="pending")
        repo.add(lp)
        ctx.commit()

        lp.mark_sent()
        repo.update(lp)
        ctx.commit()
        assert repo.get_by_id("30").status == "sent"

        lp.mark_acknowledged()
        repo.update(lp)
        ctx.commit()
        assert repo.get_by_id("30").status == "acknowledged"

        lp.mark_completed()
        repo.update(lp)
        ctx.commit()
        assert repo.get_by_id("30").status == "completed"

    def test_ndr_flag_roundtrip(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        lp = LegalProcess(id=31, case_number="LP-NDR", process_type="subpoena", ndr=True)
        repo.add(lp)
        ctx.commit()
        loaded = repo.get_by_id("31")
        assert loaded.ndr is True

    def test_ndr_defaults_false(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(32))
        ctx.commit()
        loaded = repo.get_by_id("32")
        assert loaded.ndr is False


# ---------------------------------------------------------------------------
# Optional date fields
# ---------------------------------------------------------------------------

class TestOptionalDateFields:
    def test_all_date_fields_roundtrip(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        now = datetime.utcnow().replace(microsecond=0)
        lp = LegalProcess(
            id=40,
            case_number="LP-DATES",
            process_type="search_warrant",
            submission_date=now,
            due_date=now + timedelta(days=30),
            expiration_date=now + timedelta(days=60),
            received_date=now + timedelta(days=1),
            analysis_start_date=now + timedelta(days=2),
            completed_date=now + timedelta(days=45),
        )
        repo.add(lp)
        ctx.commit()
        loaded = repo.get_by_id("40")
        assert loaded.submission_date is not None
        assert loaded.due_date is not None
        assert loaded.expiration_date is not None
        assert loaded.received_date is not None
        assert loaded.analysis_start_date is not None
        assert loaded.completed_date is not None

    def test_all_optional_dates_none(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(41))
        ctx.commit()
        loaded = repo.get_by_id("41")
        assert loaded.submission_date is None
        assert loaded.due_date is None
        assert loaded.expiration_date is None
        assert loaded.received_date is None
        assert loaded.analysis_start_date is None
        assert loaded.completed_date is None


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------

class TestSQLiteLegalProcessQueries:
    def test_get_for_case_returns_only_matching(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(1, case_number="LP-A"))
        repo.add(_lp(2, case_number="LP-A"))
        repo.add(_lp(3, case_number="LP-B"))
        ctx.commit()
        result = repo.get_for_case("LP-A")
        assert len(result) == 2
        assert all(lp.case_number == "LP-A" for lp in result)

    def test_get_for_case_empty(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        assert repo.get_for_case("NONEXISTENT") == []

    def test_get_overdue_returns_past_due_pending(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        # overdue: pending + due in past
        repo.add(_lp(1, status="pending", due_days=-5))
        # not overdue: completed + due in past
        repo.add(_lp(2, status="completed", due_days=-5))
        # not overdue: pending but due in future
        repo.add(_lp(3, status="pending", due_days=10))
        # no due_date at all
        repo.add(_lp(4, status="pending"))
        ctx.commit()
        overdue = repo.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].id == 1

    def test_get_overdue_empty_when_none(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(1, status="pending", due_days=5))
        ctx.commit()
        assert repo.get_overdue() == []

    def test_get_due_soon_returns_within_window(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        # due in 5 days (within default 7)
        repo.add(_lp(1, status="pending", due_days=5))
        # due in 10 days (outside 7)
        repo.add(_lp(2, status="pending", due_days=10))
        # completed (excluded)
        repo.add(_lp(3, status="completed", due_days=3))
        # overdue (past due_date)
        repo.add(_lp(4, status="pending", due_days=-1))
        ctx.commit()
        due_soon = repo.get_due_soon(days=7)
        assert len(due_soon) == 1
        assert due_soon[0].id == 1

    def test_get_due_soon_custom_window(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteLegalProcessRepository(ctx)
        repo.add(_lp(1, status="pending", due_days=5))
        repo.add(_lp(2, status="pending", due_days=15))
        ctx.commit()
        assert len(repo.get_due_soon(days=7)) == 1
        assert len(repo.get_due_soon(days=20)) == 2


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkLegalProcessWiring:
    def test_memory_provider(self) -> None:
        from infrastructure.persistence.repositories.legal_process_repository import (
            InMemoryLegalProcessRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.legal_processes, InMemoryLegalProcessRepository)

    def test_sqlite_provider(self, tmp_path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "lp.db"))
        assert isinstance(uow.legal_processes, SQLiteLegalProcessRepository)

    def test_sqlite_custom_override(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.legal_process_repository import (
            InMemoryLegalProcessRepository,
        )
        uow = UnitOfWork(
            provider="sqlite",
            sqlite_db_path=str(tmp_path / "lp2.db"),
            legal_process_repo=InMemoryLegalProcessRepository(),
        )
        assert isinstance(uow.legal_processes, InMemoryLegalProcessRepository)
