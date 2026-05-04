"""Integration tests for legal process repository parity across providers."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from domain.entities.legal_process import LegalProcess
from domain.entities.court_date import CourtDate
from infrastructure.persistence.db_context import SQLiteDbContext, PostgreSQLDbContext
from infrastructure.persistence.repositories.sqlite_legal_process_repository import SQLiteLegalProcessRepository
from infrastructure.persistence.repositories.postgres_legal_process_repository import PostgreSQLLegalProcessRepository
from infrastructure.persistence.repositories.sqlite_court_date_repository import SQLiteCourtDateRepository
from infrastructure.persistence.repositories.postgres_court_date_repository import PostgreSQLCourtDateRepository


def _sqlite_lp_ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "legal_process.db"))


def _sqlite_cd_ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "court_date.db"))


@pytest.mark.skipif(not True, reason="Always run local SQLite tests")
def test_sqlite_legal_process_crud(tmp_path: Path) -> None:
    """Test SQLite legal process repository CRUD operations."""
    ctx = _sqlite_lp_ctx(tmp_path)
    repo = SQLiteLegalProcessRepository(ctx)

    # Create a legal process
    lp = LegalProcess(
        id=1,
        case_number="CASE-LP-001",
        process_type="subpoena",
        provider="DA",
        status="pending",
        submission_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
        notes="Initial subpoena request",
    )
    repo.add(lp)
    ctx.commit()

    # Retrieve
    loaded = repo.get_by_id("1")
    assert loaded is not None
    assert loaded.case_number == "CASE-LP-001"
    assert loaded.process_type == "subpoena"

    # Update
    loaded.status = "sent"
    loaded.investigator_approved = True
    loaded.investigator_approved_by = "det-001"
    loaded.investigator_approved_at = datetime.utcnow()
    repo.update(loaded)
    ctx.commit()

    reloaded = repo.get_by_id("1")
    assert reloaded.status == "sent"
    assert reloaded.investigator_approved is True

    # Delete
    repo.delete("1")
    ctx.commit()
    assert repo.get_by_id("1") is None


@pytest.mark.skipif(not True, reason="Always run local SQLite tests")
def test_sqlite_legal_process_queries(tmp_path: Path) -> None:
    """Test SQLite legal process repository queries."""
    ctx = _sqlite_lp_ctx(tmp_path)
    repo = SQLiteLegalProcessRepository(ctx)

    now = datetime.utcnow()
    past = now - timedelta(days=5)
    future = now + timedelta(days=7)
    far_future = now + timedelta(days=30)

    # Add test data
    lp1 = LegalProcess(
        id=1,
        case_number="CASE-1",
        process_type="subpoena",
        status="pending",
        due_date=past,  # overdue
    )
    lp2 = LegalProcess(
        id=2,
        case_number="CASE-1",
        process_type="search_warrant",
        status="pending",
        due_date=future,  # due soon (within 7 days)
    )
    lp3 = LegalProcess(
        id=3,
        case_number="CASE-2",
        process_type="court_order",
        status="completed",
        due_date=past,  # completed so should not be in overdue
    )
    lp4 = LegalProcess(
        id=4,
        case_number="CASE-2",
        process_type="subpoena",
        status="pending",
        due_date=far_future,  # not soon
    )
    repo.add(lp1)
    repo.add(lp2)
    repo.add(lp3)
    repo.add(lp4)
    ctx.commit()

    # Test get_for_case
    case1_items = repo.get_for_case("CASE-1")
    assert len(case1_items) == 2

    # Test get_overdue
    overdue = repo.get_overdue()
    assert len(overdue) == 1
    assert overdue[0].id == 1

    # Test get_due_soon
    due_soon = repo.get_due_soon(days=7)
    assert len(due_soon) == 1
    assert due_soon[0].id == 2


@pytest.mark.skipif(not True, reason="Always run local SQLite tests")
def test_sqlite_court_date_crud(tmp_path: Path) -> None:
    """Test SQLite court date repository CRUD operations."""
    ctx = _sqlite_cd_ctx(tmp_path)
    repo = SQLiteCourtDateRepository(ctx)

    # Create a court date
    cd = CourtDate(
        id=1,
        case_number="CASE-CD-001",
        date_type="trial",
        court_date=datetime.utcnow() + timedelta(days=60),
        location="County Courthouse, Room 205",
        notes="Murder trial",
    )
    repo.add(cd)
    ctx.commit()

    # Retrieve
    loaded = repo.get_by_id("1")
    assert loaded is not None
    assert loaded.case_number == "CASE-CD-001"
    assert loaded.date_type == "trial"

    # Update
    loaded.notes = "Rescheduled - Murder trial"
    repo.update(loaded)
    ctx.commit()

    reloaded = repo.get_by_id("1")
    assert "Rescheduled" in reloaded.notes

    # Delete
    repo.delete("1")
    ctx.commit()
    assert repo.get_by_id("1") is None


@pytest.mark.skipif(not True, reason="Always run local SQLite tests")
def test_sqlite_court_date_queries(tmp_path: Path) -> None:
    """Test SQLite court date repository queries."""
    ctx = _sqlite_cd_ctx(tmp_path)
    repo = SQLiteCourtDateRepository(ctx)

    now = datetime.utcnow()
    near_future = now + timedelta(days=30)
    far_future = now + timedelta(days=100)
    past = now - timedelta(days=10)

    # Add test data
    cd1 = CourtDate(
        id=1,
        case_number="CASE-1",
        date_type="trial",
        court_date=near_future,  # upcoming
        location="Room 1",
    )
    cd2 = CourtDate(
        id=2,
        case_number="CASE-1",
        date_type="sentencing",
        court_date=far_future,  # beyond 90 days
        location="Room 2",
    )
    cd3 = CourtDate(
        id=3,
        case_number="CASE-2",
        date_type="hearing",
        court_date=past,  # in the past
        location="Room 3",
    )
    repo.add(cd1)
    repo.add(cd2)
    repo.add(cd3)
    ctx.commit()

    # Test get_for_case
    case1_dates = repo.get_for_case("CASE-1")
    assert len(case1_dates) == 2

    # Test get_upcoming (default 90 days)
    upcoming = repo.get_upcoming(days_ahead=90)
    assert len(upcoming) == 1
    assert upcoming[0].id == 1
    assert upcoming[0].date_type == "trial"


@pytest.mark.skipif(not True, reason="Always run if PostgreSQL DSN available")
def test_postgres_legal_process_crud() -> None:
    """Test PostgreSQL legal process repository CRUD operations (env-gated)."""
    import os

    pg_dsn = os.getenv("FORENSIC_PG_DSN")
    if not pg_dsn:
        pytest.skip("FORENSIC_PG_DSN not set")

    ctx = PostgreSQLDbContext(pg_dsn)
    repo = PostgreSQLLegalProcessRepository(ctx)

    # Create a legal process
    lp = LegalProcess(
        id=100,
        case_number="CASE-LP-PG-001",
        process_type="subpoena",
        provider="DA",
        status="pending",
        submission_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=30),
        notes="PostgreSQL test subpoena",
    )
    repo.add(lp)
    ctx.commit()

    # Retrieve
    loaded = repo.get_by_id("100")
    assert loaded is not None
    assert loaded.case_number == "CASE-LP-PG-001"

    # Update
    loaded.status = "sent"
    repo.update(loaded)
    ctx.commit()

    # Cleanup
    repo.delete("100")
    ctx.commit()


@pytest.mark.skipif(not True, reason="Always run if PostgreSQL DSN available")
def test_postgres_court_date_crud() -> None:
    """Test PostgreSQL court date repository CRUD operations (env-gated)."""
    import os

    pg_dsn = os.getenv("FORENSIC_PG_DSN")
    if not pg_dsn:
        pytest.skip("FORENSIC_PG_DSN not set")

    ctx = PostgreSQLDbContext(pg_dsn)
    repo = PostgreSQLCourtDateRepository(ctx)

    # Create a court date
    cd = CourtDate(
        id=100,
        case_number="CASE-CD-PG-001",
        date_type="trial",
        court_date=datetime.utcnow() + timedelta(days=60),
        location="County Courthouse, Room 205",
        notes="PostgreSQL test trial",
    )
    repo.add(cd)
    ctx.commit()

    # Retrieve
    loaded = repo.get_by_id("100")
    assert loaded is not None
    assert loaded.case_number == "CASE-CD-PG-001"

    # Cleanup
    repo.delete("100")
    ctx.commit()
