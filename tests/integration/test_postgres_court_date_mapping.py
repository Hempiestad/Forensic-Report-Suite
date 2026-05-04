"""tests/integration/test_postgres_court_date_mapping.py

PostgreSQL CourtDate repository: mapping tests (no live DB required),
UnitOfWork provider selection. Live tests gated by FORENSIC_PG_DSN.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import pytest

from domain.entities.court_date import CourtDate
from infrastructure.persistence.repositories.postgres_court_date_repository import (
    PostgreSQLCourtDateRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


_skip_pg = pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")


def _row(**overrides) -> dict:
    base: dict = {
        "id": 1,
        "case_number": "C-001",
        "date_type": "trial",
        "court_date": datetime(2027, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        "location": "Courtroom 5",
        "notes": "Jury selection.",
        "created_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _to_entity mapping (no live DB)
# ---------------------------------------------------------------------------

class TestPostgresCourtDateMapping:
    def _repo(self) -> PostgreSQLCourtDateRepository:
        return PostgreSQLCourtDateRepository.__new__(PostgreSQLCourtDateRepository)

    def test_basic_fields(self) -> None:
        repo = self._repo()
        cd = repo._to_entity(_row())
        assert isinstance(cd, CourtDate)
        assert cd.id == 1
        assert cd.case_number == "C-001"
        assert cd.date_type == "trial"

    def test_court_date_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2027, 12, 1, 9, 0, tzinfo=timezone.utc)
        cd = repo._to_entity(_row(court_date=ts))
        assert cd.court_date == ts

    def test_location_and_notes(self) -> None:
        repo = self._repo()
        cd = repo._to_entity(_row(location="Room 9", notes="Final hearing."))
        assert cd.location == "Room 9"
        assert cd.notes == "Final hearing."

    def test_optional_location_none(self) -> None:
        repo = self._repo()
        cd = repo._to_entity(_row(location=None))
        assert cd.location is None

    def test_optional_notes_none(self) -> None:
        repo = self._repo()
        cd = repo._to_entity(_row(notes=None))
        assert cd.notes is None

    def test_created_at_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cd = repo._to_entity(_row(created_at=ts))
        assert cd.created_at == ts

    def test_created_at_none_fallback(self) -> None:
        repo = self._repo()
        cd = repo._to_entity(_row(created_at=None))
        # Should fall back to a datetime, not raise
        assert isinstance(cd.created_at, datetime)

    def test_date_types_roundtrip(self) -> None:
        repo = self._repo()
        for date_type in ["trial", "sentencing", "hearing", "motion"]:
            cd = repo._to_entity(_row(date_type=date_type))
            assert cd.date_type == date_type

    def test_id_coercion_from_int(self) -> None:
        repo = self._repo()
        cd = repo._to_entity(_row(id=42))
        assert cd.id == 42
        assert isinstance(cd.id, int)


# ---------------------------------------------------------------------------
# UnitOfWork provider selection
# ---------------------------------------------------------------------------

class TestUoWPostgresCourtDateProviderSelection:
    def test_memory_provider_uses_inmemory(self) -> None:
        from infrastructure.persistence.repositories.court_date_repository import (
            InMemoryCourtDateRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.court_dates, InMemoryCourtDateRepository)

    def test_sqlite_provider_uses_sqlite(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.sqlite_court_date_repository import (
            SQLiteCourtDateRepository,
        )
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "cd.db"))
        assert isinstance(uow.court_dates, SQLiteCourtDateRepository)

    @_skip_pg
    def test_postgres_provider_uses_postgres(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.court_dates, PostgreSQLCourtDateRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (gated by FORENSIC_PG_DSN)
# ---------------------------------------------------------------------------

@_skip_pg
class TestPostgresLiveCourtDateCRUD:
    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_by_id(self) -> None:
        uow = self._uow()
        cd = CourtDate(
            id=99001,
            case_number="PG-CD-001",
            date_type="trial",
            court_date=datetime.utcnow() + timedelta(days=60),
            location="Courtroom 1",
            notes="PG test.",
        )
        try:
            uow.court_dates.add(cd)
            uow.commit()
            loaded = uow.court_dates.get_by_id("99001")
            assert loaded is not None
            assert loaded.case_number == "PG-CD-001"
            assert loaded.date_type == "trial"
        finally:
            uow.court_dates.delete("99001")
            uow.commit()

    def test_update_and_query(self) -> None:
        uow = self._uow()
        cd = CourtDate(
            id=99002,
            case_number="PG-CD-002",
            date_type="hearing",
            court_date=datetime.utcnow() + timedelta(days=30),
        )
        try:
            uow.court_dates.add(cd)
            uow.commit()

            cd.notes = "Updated for PG."
            uow.court_dates.update(cd)
            uow.commit()

            results = uow.court_dates.get_for_case("PG-CD-002")
            assert len(results) == 1
            assert results[0].notes == "Updated for PG."
        finally:
            uow.court_dates.delete("99002")
            uow.commit()
