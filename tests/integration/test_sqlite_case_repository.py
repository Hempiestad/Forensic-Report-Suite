from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from domain.entities.case import Case
from domain.enums.case_status import CaseStatus
from domain.exceptions.domain_exceptions import (
    CaseArchivedError,
    InvalidStatusTransitionError,
)
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_case_repository import SQLiteCaseRepository
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path: Path, name: str = "cases.db") -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / name))


def _new_repo(tmp_path: Path) -> tuple[SQLiteDbContext, SQLiteCaseRepository]:
    db = _ctx(tmp_path, "cases_test.db")
    repo = SQLiteCaseRepository(db)
    return db, repo


def _make_case(
    case_number: str = "C-001",
    title: str = "Test Case",
    assigned_to: str = "det.alice",
    created_by: str = "admin",
    examiner_id: str | None = None,
) -> Case:
    return Case.create(
        case_number=case_number,
        title=title,
        assigned_to=assigned_to,
        created_by=created_by,
        examiner_id=examiner_id,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════════════════════════════════

class TestSchema:
    def test_schema_version(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT MAX(version) AS v FROM schema_versions"
        ).fetchone()
        assert row["v"] >= 1

    def test_cases_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cases'"
        ).fetchone()
        assert row is not None

    def test_cases_table_has_required_columns(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        cols = {
            r["name"]
            for r in db.connection.execute("PRAGMA table_info(cases)").fetchall()
        }
        for required in (
            "case_number", "title", "assigned_to", "created_by", "status",
            "examiner_id", "review_comments", "trial_date", "sentencing_date",
            "peer_reviewers", "created_at", "modified_at", "modified_by",
        ):
            assert required in cols


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestSQLiteCaseRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case()
        repo.add(case)
        db.commit()
        loaded = repo.get_by_id("C-001")
        assert loaded is not None
        assert loaded.case_number == "C-001"
        assert loaded.title == "Test Case"

    def test_get_by_id_delegates_to_case_number(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("X-99"))
        db.commit()
        assert repo.get_by_id("X-99") is not None
        assert repo.get_by_id("X-99").case_number == "X-99"

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _new_repo(tmp_path)
        assert repo.get_by_id("NO-SUCH") is None

    def test_get_all_empty(self, tmp_path: Path) -> None:
        _, repo = _new_repo(tmp_path)
        assert repo.get_all() == []

    def test_get_all_returns_all_cases(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001"))
        repo.add(_make_case("C-002"))
        repo.add(_make_case("C-003"))
        db.commit()
        all_cases = repo.get_all()
        assert len(all_cases) == 3
        case_numbers = {c.case_number for c in all_cases}
        assert case_numbers == {"C-001", "C-002", "C-003"}

    def test_update(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case()
        repo.add(case)
        db.commit()
        case.title = "Renamed Case"
        case.modified_by = "supervisor"
        repo.update(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.title == "Renamed Case"
        assert loaded.modified_by == "supervisor"

    def test_delete(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case())
        db.commit()
        repo.delete("C-001")
        db.commit()
        assert repo.get_by_case_number("C-001") is None

    def test_exists_true(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case())
        db.commit()
        assert repo.exists("C-001") is True

    def test_exists_false(self, tmp_path: Path) -> None:
        _, repo = _new_repo(tmp_path)
        assert repo.exists("NO-SUCH") is False


# ═══════════════════════════════════════════════════════════════════════════
# Status persistence roundtrip
# ═══════════════════════════════════════════════════════════════════════════

class TestCaseStatusRoundtrip:
    def _transition_to(self, case: Case, target: CaseStatus) -> None:
        """Drive a case through the minimal path to reach *target*."""
        path = {
            CaseStatus.DRAFT: [],
            CaseStatus.UNDER_INVESTIGATION: [CaseStatus.UNDER_INVESTIGATION],
            CaseStatus.PENDING_REVIEW: [
                CaseStatus.UNDER_INVESTIGATION,
                CaseStatus.PENDING_REVIEW,
            ],
            CaseStatus.UNDER_LEGAL_REVIEW: [
                CaseStatus.UNDER_INVESTIGATION,
                CaseStatus.PENDING_REVIEW,
                CaseStatus.UNDER_LEGAL_REVIEW,
            ],
            CaseStatus.CLOSED: [
                CaseStatus.UNDER_INVESTIGATION,
                CaseStatus.PENDING_REVIEW,
                CaseStatus.UNDER_LEGAL_REVIEW,
                CaseStatus.CLOSED,
            ],
            CaseStatus.ARCHIVED: [
                CaseStatus.UNDER_INVESTIGATION,
                CaseStatus.PENDING_REVIEW,
                CaseStatus.UNDER_LEGAL_REVIEW,
                CaseStatus.CLOSED,
                CaseStatus.ARCHIVED,
            ],
        }
        for status in path[target]:
            case.transition_to(status, "tester")

    @pytest.mark.parametrize("target_status", list(CaseStatus))
    def test_all_statuses_roundtrip(self, tmp_path: Path, target_status: CaseStatus) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case(f"C-{target_status.value}")
        self._transition_to(case, target_status)
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number(f"C-{target_status.value}")
        assert loaded is not None
        assert loaded.status == target_status

    def test_status_update_persisted(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case()
        repo.add(case)
        db.commit()
        case.open_investigation("det.alice")
        repo.update(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.status == CaseStatus.UNDER_INVESTIGATION

    def test_invalid_status_string_defaults_to_draft(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case())
        db.commit()
        db.connection.execute(
            "UPDATE cases SET status = 'totally_unknown' WHERE case_number = 'C-001'"
        )
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.status == CaseStatus.DRAFT


# ═══════════════════════════════════════════════════════════════════════════
# Optional fields roundtrip
# ═══════════════════════════════════════════════════════════════════════════

class TestOptionalFieldsRoundtrip:
    def test_examiner_id_persists(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case(examiner_id="examiner-42")
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.examiner_id == "examiner-42"

    def test_examiner_id_none(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case())
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.examiner_id is None

    def test_review_comments_persists(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case()
        case.review_comments = "Looks good — proceed."
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.review_comments == "Looks good — proceed."

    def test_trial_date_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        trial = datetime(2027, 9, 15, 9, 0, 0)
        case = _make_case()
        case.trial_date = trial
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.trial_date == trial

    def test_sentencing_date_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        sentencing = datetime(2027, 11, 1, 14, 30, 0)
        case = _make_case()
        case.sentencing_date = sentencing
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.sentencing_date == sentencing

    def test_dates_none(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case())
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.trial_date is None
        assert loaded.sentencing_date is None

    def test_peer_reviewers_empty_list(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case())
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.peer_reviewers == []

    def test_peer_reviewers_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case()
        case.peer_reviewers = ["alice", "bob", "carol"]
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.peer_reviewers == ["alice", "bob", "carol"]

    def test_modified_by_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        case = _make_case()
        case.modified_by = "supervisor"
        repo.add(case)
        db.commit()
        loaded = repo.get_by_case_number("C-001")
        assert loaded.modified_by == "supervisor"


# ═══════════════════════════════════════════════════════════════════════════
# Query methods
# ═══════════════════════════════════════════════════════════════════════════

class TestSQLiteCaseRepositoryQueryMethods:
    def test_get_by_case_number_found(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("CASE-FIND"))
        db.commit()
        assert repo.get_by_case_number("CASE-FIND") is not None

    def test_get_by_case_number_missing(self, tmp_path: Path) -> None:
        _, repo = _new_repo(tmp_path)
        assert repo.get_by_case_number("NO-SUCH") is None

    def test_get_by_status_returns_matching(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        c1 = _make_case("C-001")
        c2 = _make_case("C-002")
        c3 = _make_case("C-003")
        c2.open_investigation("det")
        c3.open_investigation("det")
        repo.add(c1)
        repo.add(c2)
        repo.add(c3)
        db.commit()
        results = repo.get_by_status(CaseStatus.UNDER_INVESTIGATION)
        assert len(results) == 2
        assert all(c.status == CaseStatus.UNDER_INVESTIGATION for c in results)

    def test_get_by_status_draft_only(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001"))
        c2 = _make_case("C-002")
        c2.open_investigation("det")
        repo.add(c2)
        db.commit()
        drafts = repo.get_by_status(CaseStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].case_number == "C-001"

    def test_get_assigned_to(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001", assigned_to="det.alice"))
        repo.add(_make_case("C-002", assigned_to="det.alice"))
        repo.add(_make_case("C-003", assigned_to="det.bob"))
        db.commit()
        alice_cases = repo.get_assigned_to("det.alice")
        assert len(alice_cases) == 2
        assert all(c.assigned_to == "det.alice" for c in alice_cases)

    def test_get_assigned_to_empty(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001", assigned_to="det.alice"))
        db.commit()
        assert repo.get_assigned_to("det.nobody") == []

    def test_search_by_title(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001", title="Fraud Investigation"))
        repo.add(_make_case("C-002", title="Theft Report"))
        db.commit()
        results = repo.search("fraud")
        assert len(results) == 1
        assert results[0].case_number == "C-001"

    def test_search_by_case_number(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("CASE-ALPHA"))
        repo.add(_make_case("CASE-BETA"))
        db.commit()
        results = repo.search("alpha")
        assert len(results) == 1

    def test_search_by_assigned_to(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001", assigned_to="detective.smith"))
        repo.add(_make_case("C-002", assigned_to="detective.jones"))
        db.commit()
        results = repo.search("smith")
        assert len(results) == 1
        assert results[0].assigned_to == "detective.smith"

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001", title="UPPERCASE TITLE"))
        db.commit()
        results = repo.search("uppercase")
        assert len(results) == 1

    def test_search_no_matches(self, tmp_path: Path) -> None:
        db, repo = _new_repo(tmp_path)
        repo.add(_make_case("C-001", title="Mundane Case"))
        db.commit()
        assert repo.search("zzznomatch") == []


# ═══════════════════════════════════════════════════════════════════════════
# UnitOfWork wiring
# ═══════════════════════════════════════════════════════════════════════════

class TestUnitOfWorkCaseSQLiteWiring:
    def test_memory_provider_has_cases_repo(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert uow.cases is not None

    def test_memory_provider_cases_is_in_memory(self) -> None:
        from infrastructure.persistence.repositories.case_repository import InMemoryCaseRepository
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.cases, InMemoryCaseRepository)

    def test_sqlite_provider_has_sqlite_cases(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow.db"))
        assert isinstance(uow.cases, SQLiteCaseRepository)

    def test_sqlite_provider_persists_case(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow.db"))
        case = _make_case("UOW-001")
        with uow:
            uow.cases.add(case)
        verify_db = _ctx(tmp_path, "uow.db")
        verify = SQLiteCaseRepository(verify_db)
        loaded = verify.get_by_case_number("UOW-001")
        assert loaded is not None
        assert loaded.title == "Test Case"

    def test_custom_case_repo_override(self) -> None:
        from infrastructure.persistence.repositories.case_repository import InMemoryCaseRepository
        custom = InMemoryCaseRepository()
        uow = UnitOfWork(provider="memory", case_repo=custom)
        assert uow.cases is custom


# ═══════════════════════════════════════════════════════════════════════════
# Original function-based tests (preserved)
# ═══════════════════════════════════════════════════════════════════════════


def test_sqlite_case_repository_crud(tmp_path: Path) -> None:
    db, repo = _new_repo(tmp_path)
    case = Case.create("CASE-SQL-1", "SQLite Case", "det.one", "admin")

    repo.add(case)
    db.commit()

    loaded = repo.get_by_case_number("CASE-SQL-1")
    assert loaded is not None
    assert loaded.title == "SQLite Case"

    loaded.title = "SQLite Case Updated"
    loaded.modified_by = "det.two"
    repo.update(loaded)
    db.commit()

    updated = repo.get_by_case_number("CASE-SQL-1")
    assert updated is not None
    assert updated.title == "SQLite Case Updated"
    assert updated.modified_by == "det.two"

    repo.delete("CASE-SQL-1")
    db.commit()
    assert repo.get_by_case_number("CASE-SQL-1") is None


def test_sqlite_case_repository_queries(tmp_path: Path) -> None:
    db, repo = _new_repo(tmp_path)

    c1 = Case.create("CASE-SQL-2", "Alpha Fraud", "det.one", "admin")
    c2 = Case.create("CASE-SQL-3", "Beta Theft", "det.one", "admin")
    c3 = Case.create("CASE-SQL-4", "Gamma Fraud", "det.two", "admin")

    c2.status = CaseStatus.UNDER_INVESTIGATION
    c3.status = CaseStatus.UNDER_INVESTIGATION

    repo.add(c1)
    repo.add(c2)
    repo.add(c3)
    db.commit()

    assigned = repo.get_assigned_to("det.one")
    assert len(assigned) == 2

    by_status = repo.get_by_status(CaseStatus.UNDER_INVESTIGATION)
    assert len(by_status) == 2

    searched = repo.search("fraud")
    assert len(searched) == 2


def test_unit_of_work_sqlite_case_mode(tmp_path: Path) -> None:
    db = SQLiteDbContext(str(tmp_path / "uow_sqlite.db"))
    uow = UnitOfWork(db_context=db, use_sqlite_for_cases=True)

    with uow:
        uow.cases.add(Case.create("CASE-SQL-5", "UOW SQLite", "det.three", "admin"))

    verify_repo = SQLiteCaseRepository(db)
    loaded = verify_repo.get_by_case_number("CASE-SQL-5")
    assert loaded is not None
    assert loaded.title == "UOW SQLite"
