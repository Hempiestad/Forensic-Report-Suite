"""tests/integration/test_sqlite_audit_repository.py

Phase 3 continuation — SQLite AuditEntry repository integration tests.

Covers:
- Schema migration presence for audit_entries
- CRUD behavior
- Chronological query behavior (get_for_case, get_recent, get_last_entry_for_case)
- JSON details round-trip
- UnitOfWork provider wiring for audits
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from domain.entities.audit_entry import AuditEntry
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.audit_repository import InMemoryAuditRepository
from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
from infrastructure.persistence.unit_of_work import UnitOfWork


def _ctx(tmp_path: Path, filename: str = "audit.db") -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / filename))


def _repo(tmp_path: Path) -> tuple[SQLiteDbContext, SQLiteAuditRepository]:
    db = _ctx(tmp_path)
    return db, SQLiteAuditRepository(db)


def _entry(case_number: str, event_type: str, by: str, details: dict | None = None) -> AuditEntry:
    return AuditEntry.create(
        case_number=case_number,
        event_type=event_type,
        performed_by=by,
        details=details or {},
    )


class TestSchema:
    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10

    def test_audit_entries_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_entries'"
        ).fetchone()
        assert row is not None


class TestSQLiteAuditRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        entry = _entry("CASE-001", "CASE_CREATED", "alice", {"source": "import"})
        repo.add(entry)
        db.commit()

        assert entry.id is not None
        loaded = repo.get_by_id(str(entry.id))
        assert loaded is not None
        assert loaded.case_number == "CASE-001"
        assert loaded.event_type == "CASE_CREATED"
        assert loaded.performed_by == "alice"
        assert loaded.details == {"source": "import"}

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_by_id("99999") is None

    def test_get_all_returns_ordered_rows(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        e1 = _entry("CASE-001", "A", "alice")
        e2 = _entry("CASE-001", "B", "bob")
        e1.timestamp = datetime.utcnow() - timedelta(minutes=2)
        e1.recompute_hash()
        e2.timestamp = datetime.utcnow() - timedelta(minutes=1)
        e2.recompute_hash()
        repo.add(e1)
        repo.add(e2)
        db.commit()

        all_rows = repo.get_all()
        assert len(all_rows) == 2
        assert all_rows[0].event_type == "A"
        assert all_rows[1].event_type == "B"

    def test_update_persists_changes(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        entry = _entry("CASE-001", "CASE_CREATED", "alice", {"x": 1})
        repo.add(entry)
        db.commit()

        entry.event_type = "CASE_UPDATED"
        entry.details = {"x": 2, "note": "patched"}
        entry.recompute_hash()
        repo.update(entry)
        db.commit()

        loaded = repo.get_by_id(str(entry.id))
        assert loaded is not None
        assert loaded.event_type == "CASE_UPDATED"
        assert loaded.details["x"] == 2
        assert loaded.details["note"] == "patched"

    def test_delete_removes_row(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        entry = _entry("CASE-001", "CASE_CREATED", "alice")
        repo.add(entry)
        db.commit()

        repo.delete(str(entry.id))
        db.commit()

        assert repo.get_by_id(str(entry.id)) is None
        assert not repo.exists(str(entry.id))

    def test_exists_true_false(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        entry = _entry("CASE-001", "CASE_CREATED", "alice")
        repo.add(entry)
        db.commit()

        assert repo.exists(str(entry.id))
        assert not repo.exists("123456")


class TestSQLiteAuditRepositoryQueries:
    def test_get_for_case_filters_and_orders(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        e1 = _entry("CASE-A", "A", "alice")
        e2 = _entry("CASE-A", "B", "bob")
        e3 = _entry("CASE-B", "C", "charlie")
        e1.timestamp = datetime.utcnow() - timedelta(minutes=5)
        e1.recompute_hash()
        e2.timestamp = datetime.utcnow() - timedelta(minutes=1)
        e2.recompute_hash()
        repo.add(e1)
        repo.add(e2)
        repo.add(e3)
        db.commit()

        rows = repo.get_for_case("CASE-A")
        assert len(rows) == 2
        assert [r.event_type for r in rows] == ["A", "B"]

    def test_get_recent_limit(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        for i in range(5):
            e = _entry("CASE-R", f"EV-{i}", "alice")
            e.timestamp = datetime.utcnow() + timedelta(seconds=i)
            e.recompute_hash()
            repo.add(e)
        db.commit()

        rows = repo.get_recent(limit=3)
        assert len(rows) == 3
        # Descending timestamp means newest first
        assert rows[0].event_type == "EV-4"
        assert rows[1].event_type == "EV-3"
        assert rows[2].event_type == "EV-2"

    def test_get_last_entry_for_case(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        e1 = _entry("CASE-Z", "OLD", "alice")
        e2 = _entry("CASE-Z", "NEW", "alice")
        e1.timestamp = datetime.utcnow() - timedelta(hours=1)
        e1.recompute_hash()
        e2.timestamp = datetime.utcnow()
        e2.recompute_hash()
        repo.add(e1)
        repo.add(e2)
        db.commit()

        tail = repo.get_last_entry_for_case("CASE-Z")
        assert tail is not None
        assert tail.event_type == "NEW"

    def test_get_last_entry_for_case_none(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_last_entry_for_case("NO-CASE") is None

    def test_details_json_roundtrip_nested_types(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        payload = {
            "count": 2,
            "items": ["disk", "phone"],
            "meta": {"reviewed": True, "score": 9.5},
        }
        entry = _entry("CASE-JSON", "DETAILS_ADDED", "alice", payload)
        repo.add(entry)
        db.commit()

        loaded = repo.get_by_id(str(entry.id))
        assert loaded is not None
        assert loaded.details == payload


class TestUnitOfWorkAuditWiring:
    def test_memory_provider_has_inmemory_audits(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.audits, InMemoryAuditRepository)

    def test_sqlite_provider_has_sqlite_audits(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow-audit.db"))
        assert isinstance(uow.audits, SQLiteAuditRepository)

    def test_custom_audit_repo_override(self) -> None:
        custom = InMemoryAuditRepository()
        uow = UnitOfWork(provider="memory", audit_repo=custom)
        assert uow.audits is custom
