"""tests/integration/test_sqlite_court_date_repository.py

SQLite CourtDate repository: schema check, full CRUD, query methods,
UnitOfWork wiring — all with isolated tmp_path databases.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from domain.entities.court_date import CourtDate
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_court_date_repository import (
    SQLiteCourtDateRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _ctx(tmp_path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "court_date.db"))


def _cd(
    id: int,
    case_number: str = "C-001",
    date_type: str = "trial",
    days_from_now: int = 30,
) -> CourtDate:
    return CourtDate(
        id=id,
        case_number=case_number,
        date_type=date_type,
        court_date=datetime.utcnow() + timedelta(days=days_from_now),
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_court_dates_table_exists(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        row = ctx.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='court_dates'"
        ).fetchone()
        assert row is not None

    def test_schema_version(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        row = ctx.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestSQLiteCourtDateRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        cd = _cd(1, case_number="C-CRUD-001")
        repo.add(cd)
        ctx.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.case_number == "C-CRUD-001"
        assert loaded.id == 1

    def test_get_by_id_returns_none_for_missing(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        assert repo.get_by_id("999") is None

    def test_get_all(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        repo.add(_cd(1))
        repo.add(_cd(2))
        ctx.commit()
        all_items = repo.get_all()
        assert len(all_items) == 2

    def test_update(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        cd = CourtDate(
            id=10,
            case_number="C-UPD",
            date_type="hearing",
            court_date=datetime.utcnow() + timedelta(days=20),
            location="Room A",
            notes="Original note",
        )
        repo.add(cd)
        ctx.commit()

        cd.notes = "Updated note"
        cd.location = "Room B"
        repo.update(cd)
        ctx.commit()

        reloaded = repo.get_by_id("10")
        assert reloaded.notes == "Updated note"
        assert reloaded.location == "Room B"

    def test_delete(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        repo.add(_cd(5))
        ctx.commit()
        repo.delete("5")
        ctx.commit()
        assert repo.get_by_id("5") is None

    def test_exists_true(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        repo.add(_cd(7))
        ctx.commit()
        assert repo.exists("7") is True

    def test_exists_false(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        assert repo.exists("99") is False


# ---------------------------------------------------------------------------
# Date type and optional field roundtrips
# ---------------------------------------------------------------------------

class TestCourtDateFieldRoundtrips:
    def test_date_types_roundtrip(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        for i, dt in enumerate(["trial", "sentencing", "hearing", "motion"], start=1):
            cd = CourtDate(
                id=i,
                case_number="C-TYPE",
                date_type=dt,
                court_date=datetime.utcnow() + timedelta(days=10 + i),
            )
            repo.add(cd)
        ctx.commit()
        all_items = repo.get_all()
        types = {c.date_type for c in all_items}
        assert types == {"trial", "sentencing", "hearing", "motion"}

    def test_location_and_notes_persist(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        cd = CourtDate(
            id=20,
            case_number="C-OPT",
            date_type="trial",
            court_date=datetime.utcnow() + timedelta(days=45),
            location="County Courthouse, Room 12",
            notes="Key witness present.",
        )
        repo.add(cd)
        ctx.commit()
        loaded = repo.get_by_id("20")
        assert loaded.location == "County Courthouse, Room 12"
        assert loaded.notes == "Key witness present."

    def test_optional_fields_none(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        cd = CourtDate(
            id=21,
            case_number="C-NIL",
            date_type="hearing",
            court_date=datetime.utcnow() + timedelta(days=5),
            location=None,
            notes=None,
        )
        repo.add(cd)
        ctx.commit()
        loaded = repo.get_by_id("21")
        assert loaded.location is None
        assert loaded.notes is None

    def test_court_date_roundtrip(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        future = datetime(2027, 6, 15, 9, 30, 0)
        cd = CourtDate(id=22, case_number="C-DT", date_type="trial", court_date=future)
        repo.add(cd)
        ctx.commit()
        loaded = repo.get_by_id("22")
        assert loaded.court_date.year == 2027
        assert loaded.court_date.month == 6
        assert loaded.court_date.day == 15


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------

class TestSQLiteCourtDateQueries:
    def test_get_for_case_returns_only_matching(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        repo.add(_cd(1, case_number="C-A"))
        repo.add(_cd(2, case_number="C-A"))
        repo.add(_cd(3, case_number="C-B"))
        ctx.commit()
        result = repo.get_for_case("C-A")
        assert len(result) == 2
        assert all(c.case_number == "C-A" for c in result)

    def test_get_for_case_empty(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        assert repo.get_for_case("NONEXISTENT") == []

    def test_get_upcoming_returns_dates_within_window(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        # within 90 days
        repo.add(_cd(1, days_from_now=30))
        # beyond 90 days
        repo.add(_cd(2, days_from_now=120))
        # in the past
        repo.add(_cd(3, days_from_now=-5))
        ctx.commit()
        upcoming = repo.get_upcoming(days_ahead=90)
        assert len(upcoming) == 1
        assert upcoming[0].id == 1

    def test_get_upcoming_ordered_by_date(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        repo.add(_cd(1, days_from_now=60))
        repo.add(_cd(2, days_from_now=10))
        repo.add(_cd(3, days_from_now=30))
        ctx.commit()
        upcoming = repo.get_upcoming(days_ahead=90)
        dates = [c.court_date for c in upcoming]
        assert dates == sorted(dates)

    def test_get_upcoming_no_results(self, tmp_path) -> None:
        ctx = _ctx(tmp_path)
        repo = SQLiteCourtDateRepository(ctx)
        # only past dates
        repo.add(_cd(1, days_from_now=-10))
        ctx.commit()
        assert repo.get_upcoming(days_ahead=30) == []


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkCourtDateWiring:
    def test_memory_provider(self) -> None:
        from infrastructure.persistence.repositories.court_date_repository import (
            InMemoryCourtDateRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.court_dates, InMemoryCourtDateRepository)

    def test_sqlite_provider(self, tmp_path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "cd.db"))
        assert isinstance(uow.court_dates, SQLiteCourtDateRepository)

    def test_sqlite_custom_override(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.court_date_repository import (
            InMemoryCourtDateRepository,
        )
        uow = UnitOfWork(
            provider="sqlite",
            sqlite_db_path=str(tmp_path / "cd2.db"),
            court_date_repo=InMemoryCourtDateRepository(),
        )
        assert isinstance(uow.court_dates, InMemoryCourtDateRepository)
