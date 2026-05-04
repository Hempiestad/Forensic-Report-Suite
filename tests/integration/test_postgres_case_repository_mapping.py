"""tests/integration/test_postgres_case_repository_mapping.py

PostgreSQL Case repository mapping tests.

Mapping tests exercise `_to_entity`, `_parse_status`, and `_parse_reviewers`
in isolation (no live DB required).  Live-DB tests are gated by the
FORENSIC_PG_DSN environment variable.
"""
from __future__ import annotations

import os
from datetime import datetime

import pytest

from domain.entities.case import Case
from domain.enums.case_status import CaseStatus
from infrastructure.persistence.db_context import PostgreSQLDbContext
from infrastructure.persistence.repositories.postgres_case_repository import (
    PostgreSQLCaseRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


_skip_pg = pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")

_NOW = datetime(2026, 1, 1, 12, 0, 0)


def _case_row(**overrides) -> dict:
    """Minimal case row as psycopg3 dict_row would return."""
    base: dict = {
        "case_number": "C-PG-001",
        "title": "Postgres Case",
        "assigned_to": "det.pg",
        "created_by": "admin",
        "status": "draft",
        "examiner_id": None,
        "review_comments": None,
        "trial_date": None,
        "sentencing_date": None,
        "created_at": _NOW,
        "modified_at": _NOW,
        "modified_by": None,
        "peer_reviewers": None,
    }
    base.update(overrides)
    return base


def _mapper() -> PostgreSQLCaseRepository:
    """Return repo without a live connection — only static/mapping methods used."""
    return PostgreSQLCaseRepository.__new__(PostgreSQLCaseRepository)


# ---------------------------------------------------------------------------
# _to_entity mapping (no live DB)
# ---------------------------------------------------------------------------

class TestPostgresCaseEntityMapping:
    """Unit-tests for row → Case entity mapping."""

    def test_basic_fields_mapped(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row())
        assert isinstance(case, Case)
        assert case.case_number == "C-PG-001"
        assert case.title == "Postgres Case"
        assert case.assigned_to == "det.pg"
        assert case.created_by == "admin"

    def test_status_mapped_from_string(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row(status="under_investigation"))
        assert case.status == CaseStatus.UNDER_INVESTIGATION

    def test_all_statuses_mapped(self) -> None:
        repo = _mapper()
        for status in CaseStatus:
            case = repo._to_entity(_case_row(status=status.value))
            assert case.status == status

    def test_examiner_id_none(self) -> None:
        repo = _mapper()
        assert repo._to_entity(_case_row(examiner_id=None)).examiner_id is None

    def test_examiner_id_present(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row(examiner_id="examiner-7"))
        assert case.examiner_id == "examiner-7"

    def test_review_comments_none(self) -> None:
        repo = _mapper()
        assert repo._to_entity(_case_row(review_comments=None)).review_comments is None

    def test_review_comments_present(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row(review_comments="Approved"))
        assert case.review_comments == "Approved"

    def test_trial_date_none(self) -> None:
        repo = _mapper()
        assert repo._to_entity(_case_row(trial_date=None)).trial_date is None

    def test_trial_date_datetime_passthrough(self) -> None:
        repo = _mapper()
        trial = datetime(2027, 6, 15, 9, 0, 0)
        case = repo._to_entity(_case_row(trial_date=trial))
        assert case.trial_date == trial

    def test_sentencing_date_datetime_passthrough(self) -> None:
        repo = _mapper()
        sentencing = datetime(2027, 10, 1, 10, 0, 0)
        case = repo._to_entity(_case_row(sentencing_date=sentencing))
        assert case.sentencing_date == sentencing

    def test_created_at_datetime_passthrough(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row(created_at=_NOW))
        assert case.created_at == _NOW

    def test_modified_at_datetime_passthrough(self) -> None:
        repo = _mapper()
        mod = datetime(2026, 3, 1)
        case = repo._to_entity(_case_row(modified_at=mod))
        assert case.modified_at == mod

    def test_modified_by_none(self) -> None:
        repo = _mapper()
        assert repo._to_entity(_case_row(modified_by=None)).modified_by is None

    def test_modified_by_present(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row(modified_by="supervisor"))
        assert case.modified_by == "supervisor"

    def test_peer_reviewers_none_becomes_empty_list(self) -> None:
        repo = _mapper()
        case = repo._to_entity(_case_row(peer_reviewers=None))
        assert case.peer_reviewers == []

    def test_peer_reviewers_from_list(self) -> None:
        """psycopg3 may return JSONB as a native list."""
        repo = _mapper()
        case = repo._to_entity(_case_row(peer_reviewers=["alice", "bob"]))
        assert case.peer_reviewers == ["alice", "bob"]

    def test_peer_reviewers_from_json_string(self) -> None:
        """Adapter may return peer_reviewers as a JSON string."""
        repo = _mapper()
        case = repo._to_entity(_case_row(peer_reviewers='["x","y"]'))
        assert case.peer_reviewers == ["x", "y"]


# ---------------------------------------------------------------------------
# _parse_status
# ---------------------------------------------------------------------------

class TestParseStatus:
    @pytest.mark.parametrize("status", list(CaseStatus))
    def test_all_valid_statuses_round_trip(self, status: CaseStatus) -> None:
        assert PostgreSQLCaseRepository._parse_status(status.value) == status

    def test_invalid_falls_back_to_draft(self) -> None:
        assert PostgreSQLCaseRepository._parse_status("unknown_value") == CaseStatus.DRAFT

    def test_empty_string_falls_back_to_draft(self) -> None:
        assert PostgreSQLCaseRepository._parse_status("") == CaseStatus.DRAFT


# ---------------------------------------------------------------------------
# _parse_reviewers
# ---------------------------------------------------------------------------

class TestParseReviewers:
    def test_none_returns_empty(self) -> None:
        assert PostgreSQLCaseRepository._parse_reviewers(None) == []

    def test_empty_string_returns_empty(self) -> None:
        assert PostgreSQLCaseRepository._parse_reviewers("") == []

    def test_native_list_returned_as_is(self) -> None:
        assert PostgreSQLCaseRepository._parse_reviewers(["a", "b"]) == ["a", "b"]

    def test_json_string_parsed(self) -> None:
        assert PostgreSQLCaseRepository._parse_reviewers('["x","y"]') == ["x", "y"]

    def test_invalid_json_returns_empty(self) -> None:
        assert PostgreSQLCaseRepository._parse_reviewers("not-json") == []

    def test_non_string_values_coerced_to_str(self) -> None:
        result = PostgreSQLCaseRepository._parse_reviewers([1, 2, 3])
        assert result == ["1", "2", "3"]


# ---------------------------------------------------------------------------
# UnitOfWork provider selection
# ---------------------------------------------------------------------------

class TestUoWPostgresCaseProviderSelection:
    def test_postgres_provider_creates_pg_case_repo(self) -> None:
        dsn = _pg_dsn() or "postgresql://user:pass@localhost:5432/forensic"
        uow = UnitOfWork(provider="postgres", postgres_dsn=dsn)
        assert isinstance(uow.cases, PostgreSQLCaseRepository)

    def test_memory_provider_does_not_create_pg_repo(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert not isinstance(uow.cases, PostgreSQLCaseRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL CRUD (skipped unless FORENSIC_PG_DSN is set)
# ---------------------------------------------------------------------------

class TestPostgresLiveCaseCRUD:
    @_skip_pg
    def test_add_and_get_by_case_number(self) -> None:
        from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
        db = PostgreSQLPooledDbContext(_pg_dsn())
        repo = PostgreSQLCaseRepository(db)
        case = Case.create("PG-LIVE-99301", "PG Live Case", "pg.user", "pg.admin")
        try:
            repo.add(case)
            db.commit()
            loaded = repo.get_by_case_number("PG-LIVE-99301")
            assert loaded is not None
            assert loaded.title == "PG Live Case"
        finally:
            repo.delete("PG-LIVE-99301")
            db.commit()

    @_skip_pg
    def test_update_live(self) -> None:
        from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
        db = PostgreSQLPooledDbContext(_pg_dsn())
        repo = PostgreSQLCaseRepository(db)
        case = Case.create("PG-LIVE-99302", "Original Title", "pg.user", "pg.admin")
        try:
            repo.add(case)
            db.commit()
            case.title = "Updated Title"
            case.modified_by = "pg.supervisor"
            repo.update(case)
            db.commit()
            loaded = repo.get_by_case_number("PG-LIVE-99302")
            assert loaded.title == "Updated Title"
            assert loaded.modified_by == "pg.supervisor"
        finally:
            repo.delete("PG-LIVE-99302")
            db.commit()

    @_skip_pg
    def test_delete_live(self) -> None:
        from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
        db = PostgreSQLPooledDbContext(_pg_dsn())
        repo = PostgreSQLCaseRepository(db)
        case = Case.create("PG-LIVE-99303", "Delete Me", "pg.user", "pg.admin")
        repo.add(case)
        db.commit()
        repo.delete("PG-LIVE-99303")
        db.commit()
        assert repo.get_by_case_number("PG-LIVE-99303") is None


# ---------------------------------------------------------------------------
# Original function-based tests (preserved)
# ---------------------------------------------------------------------------


def test_postgres_case_repository_parse_status_fallback() -> None:
    assert PostgreSQLCaseRepository._parse_status("draft") == CaseStatus.DRAFT
    assert PostgreSQLCaseRepository._parse_status("invalid_status") == CaseStatus.DRAFT


def test_postgres_case_repository_parse_reviewers_variants() -> None:
    assert PostgreSQLCaseRepository._parse_reviewers(None) == []
    assert PostgreSQLCaseRepository._parse_reviewers(["a", "b"]) == ["a", "b"]
    assert PostgreSQLCaseRepository._parse_reviewers('["x","y"]') == ["x", "y"]
    assert PostgreSQLCaseRepository._parse_reviewers("not-json") == []


def test_postgres_context_is_lazy() -> None:
    # Constructing context must not connect until .connection is accessed.
    ctx = PostgreSQLDbContext("postgresql://user:pass@localhost:5432/forensic")
    assert ctx._conn is None
