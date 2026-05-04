"""tests/integration/test_sqlite_report_repository.py

Integration tests for SQLiteReportRepository covering:
- Schema presence
- CRUD (add / get_by_id / update / delete / exists / get_all)
- Queries (get_for_case, get_finalized)
- Status roundtrip for all ReportStatus values
- Appendices JSON roundtrip (add / remove)
- Status transitions persisted correctly
- UnitOfWork provider wiring
"""
from __future__ import annotations

from pathlib import Path

from domain.entities.report import Report
from domain.enums.report_status import ReportStatus
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.report_repository import InMemoryReportRepository
from infrastructure.persistence.repositories.sqlite_report_repository import SQLiteReportRepository
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "reports.db"))


def _repo(tmp_path: Path) -> tuple[SQLiteDbContext, SQLiteReportRepository]:
    db = _ctx(tmp_path)
    return db, SQLiteReportRepository(db)


def _report(id: int = 1, case_number: str = "CASE-001", created_by: str = "alice") -> Report:
    return Report.create(id=id, case_number=case_number, created_by=created_by)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_reports_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
        ).fetchone()
        assert row is not None

    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestSQLiteReportRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        repo.add(report)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.id == 1
        assert loaded.case_number == "CASE-001"
        assert loaded.created_by == "alice"
        assert loaded.status == ReportStatus.DRAFT

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_by_id("99999") is None

    def test_get_all_returns_all_rows(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_report(id=1, case_number="C-001"))
        repo.add(_report(id=2, case_number="C-002"))
        db.commit()

        rows = repo.get_all()
        assert len(rows) == 2
        case_numbers = {r.case_number for r in rows}
        assert case_numbers == {"C-001", "C-002"}

    def test_update_persists_changes(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        report.report_html = "<p>Draft content</p>"
        repo.add(report)
        db.commit()

        report.report_html = "<p>Updated content</p>"
        report.modified_by = "bob"
        repo.update(report)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.report_html == "<p>Updated content</p>"
        assert loaded.modified_by == "bob"

    def test_delete_removes_row(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        repo.add(report)
        db.commit()

        repo.delete("1")
        db.commit()

        assert repo.get_by_id("1") is None
        assert not repo.exists("1")

    def test_exists_true_and_false(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_report(id=5))
        db.commit()

        assert repo.exists("5")
        assert not repo.exists("99")


# ---------------------------------------------------------------------------
# Status roundtrip
# ---------------------------------------------------------------------------

class TestReportStatusRoundtrip:
    def test_all_statuses_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        for i, status in enumerate(ReportStatus, start=1):
            r = Report(
                id=i,
                case_number=f"C-{i}",
                status=status,
                created_by="tester",
            )
            repo.add(r)
        db.commit()

        for i, status in enumerate(ReportStatus, start=1):
            loaded = repo.get_by_id(str(i))
            assert loaded is not None
            assert loaded.status == status

    def test_status_transition_persisted(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        repo.add(report)
        db.commit()

        report.submit_for_review("alice")
        repo.update(report)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.status == ReportStatus.IN_REVIEW

    def test_unknown_status_falls_back_to_draft(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        repo.add(report)
        db.commit()

        db.connection.execute("UPDATE reports SET status = 'unknown_garbage' WHERE id = 1")
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.status == ReportStatus.DRAFT


# ---------------------------------------------------------------------------
# Appendices
# ---------------------------------------------------------------------------

class TestReportAppendicesRoundtrip:
    def test_empty_appendices_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_report())
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.appendices == []

    def test_appendices_persist_and_reload(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        report.add_appendix("/files/exhibit_a.pdf", "alice")
        report.add_appendix("/files/chain_of_custody.pdf", "alice")
        repo.add(report)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert "/files/exhibit_a.pdf" in loaded.appendices
        assert "/files/chain_of_custody.pdf" in loaded.appendices

    def test_removed_appendix_not_reloaded(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        report.add_appendix("/files/old.pdf", "alice")
        report.add_appendix("/files/keep.pdf", "alice")
        repo.add(report)
        db.commit()

        report.remove_appendix("/files/old.pdf", "alice")
        repo.update(report)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert "/files/old.pdf" not in loaded.appendices
        assert "/files/keep.pdf" in loaded.appendices


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class TestSQLiteReportQueries:
    def test_get_for_case_returns_report(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_report(id=1, case_number="CASE-X"))
        repo.add(_report(id=2, case_number="CASE-Y"))
        db.commit()

        found = repo.get_for_case("CASE-X")
        assert found is not None
        assert found.case_number == "CASE-X"

    def test_get_for_case_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_for_case("NONEXISTENT") is None

    def test_get_finalized_returns_only_finalized(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        repo.add(report)
        db.commit()

        # Advance through the state machine to FINALIZED
        report.submit_for_review("alice")
        report.mark_peer_reviewed("bob")
        report.finalize("charlie", pdf_hash="abc123")
        repo.update(report)
        db.commit()

        result = repo.get_finalized("1")
        assert result is not None
        assert result.status == ReportStatus.FINALIZED
        assert result.finalized_by == "charlie"
        assert result.final_pdf_hash == "abc123"

    def test_get_finalized_on_draft_returns_none(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_report())
        db.commit()
        assert repo.get_finalized("1") is None

    def test_finalized_at_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        report = _report()
        repo.add(report)
        db.commit()

        report.submit_for_review("alice")
        report.mark_peer_reviewed("bob")
        report.finalize("charlie")
        repo.update(report)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.finalized_at is not None


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkReportWiring:
    def test_memory_provider_uses_inmemory_reports(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.reports, InMemoryReportRepository)

    def test_sqlite_provider_uses_sqlite_reports(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow.db"))
        assert isinstance(uow.reports, SQLiteReportRepository)

    def test_custom_report_repo_override(self) -> None:
        custom = InMemoryReportRepository()
        uow = UnitOfWork(provider="memory", report_repo=custom)
        assert uow.reports is custom
