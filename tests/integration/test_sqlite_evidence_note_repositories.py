"""tests/integration/test_sqlite_evidence_note_repositories.py

Integration tests for Phase 7:
  - SQLiteEvidenceRepository CRUD + queries
  - SQLiteNoteRepository CRUD + queries
  - UnitOfWork.evidence / UnitOfWork.notes wiring
  - SQLite schema v6 (evidence) + v7 (notes) migration correctness
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pytest

from domain.entities.evidence import Evidence
from domain.entities.note import Note
from domain.enums.evidence_status import EvidenceStatus
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.sqlite_evidence_repository import SQLiteEvidenceRepository
from infrastructure.persistence.repositories.sqlite_note_repository import SQLiteNoteRepository
from infrastructure.persistence.unit_of_work import UnitOfWork


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _ctx(tmp_path: Path, filename: str = "test.db") -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / filename))


def _evidence_repo(tmp_path: Path):
    db = _ctx(tmp_path)
    return db, SQLiteEvidenceRepository(db)


def _note_repo(tmp_path: Path):
    db = _ctx(tmp_path)
    return db, SQLiteNoteRepository(db)


def _make_evidence(id: int = 1, case: str = "C-001", item: str = "E-001") -> Evidence:
    return Evidence.create(id=id, case_number=case, evidence_item_number=item, item_type="HDD")


def _make_note(id: str = "note-1", case: str = "C-001") -> Note:
    return Note.create(id=id, case_number=case, title="Test Note", body="Note body", created_by="alice")


# ═══════════════════════════════════════════════════════════════════════════
# Schema migration tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSchemaMigrations:
    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10

    def test_evidence_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence'"
        ).fetchone()
        assert row is not None

    def test_notes_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notes'"
        ).fetchone()
        assert row is not None

    def test_evidence_indexes_exist(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        rows = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_evidence%'"
        ).fetchall()
        names = {r["name"] for r in rows}
        assert "idx_evidence_case_number" in names
        assert "idx_evidence_status" in names
        assert "idx_evidence_case_item" in names

    def test_notes_indexes_exist(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        rows = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_notes%'"
        ).fetchall()
        names = {r["name"] for r in rows}
        assert "idx_notes_case_number" in names
        assert "idx_notes_created_at" in names

    def test_migration_is_idempotent(self, tmp_path: Path) -> None:
        """Opening the same database twice should not raise."""
        path = str(tmp_path / "idempotent.db")
        db1 = SQLiteDbContext(path)
        _ = db1.connection  # triggers migration
        db1.close()
        db2 = SQLiteDbContext(path)
        _ = db2.connection  # already at v7 — should not re-run migrations
        db2.close()


# ═══════════════════════════════════════════════════════════════════════════
# SQLiteEvidenceRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestSQLiteEvidenceRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence()
        repo.add(ev)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.case_number == "C-001"
        assert loaded.evidence_item_number == "E-001"

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _evidence_repo(tmp_path)
        assert repo.get_by_id("99") is None

    def test_get_all(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        repo.add(_make_evidence(1, "C-001", "E-001"))
        repo.add(_make_evidence(2, "C-001", "E-002"))
        db.commit()
        all_ev = repo.get_all()
        assert len(all_ev) == 2

    def test_update(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence()
        repo.add(ev)
        db.commit()
        ev.physical_description = "500GB SSD"
        repo.update(ev)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.physical_description == "500GB SSD"

    def test_delete(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence()
        repo.add(ev)
        db.commit()
        repo.delete("1")
        db.commit()
        assert repo.get_by_id("1") is None

    def test_exists(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence()
        repo.add(ev)
        db.commit()
        assert repo.exists("1") is True
        assert repo.exists("99") is False


class TestSQLiteEvidenceRepositoryQueries:
    def test_get_for_case(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        repo.add(_make_evidence(1, "C-001", "E-001"))
        repo.add(_make_evidence(2, "C-001", "E-002"))
        repo.add(_make_evidence(3, "C-002", "E-001"))
        db.commit()
        results = repo.get_for_case("C-001")
        assert len(results) == 2
        assert all(e.case_number == "C-001" for e in results)

    def test_get_by_item_number(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence(1, "C-001", "E-001")
        repo.add(ev)
        db.commit()
        found = repo.get_by_item_number("C-001", "E-001")
        assert found is not None
        assert found.id == 1

    def test_get_by_item_number_missing(self, tmp_path: Path) -> None:
        _, repo = _evidence_repo(tmp_path)
        assert repo.get_by_item_number("C-001", "E-999") is None

    def test_get_by_status(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev1 = _make_evidence(1, "C-001", "E-001")
        ev2 = _make_evidence(2, "C-001", "E-002")
        ev2.start_imaging()
        repo.add(ev1)
        repo.add(ev2)
        db.commit()
        not_imaged = repo.get_by_status(EvidenceStatus.NOT_IMAGED)
        assert len(not_imaged) == 1
        assert not_imaged[0].id == 1

    def test_status_transition_persists(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence()
        repo.add(ev)
        db.commit()
        ev.start_imaging()
        ev.mark_imaged()
        repo.update(ev)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.status == EvidenceStatus.IMAGED

    def test_all_fields_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _evidence_repo(tmp_path)
        ev = _make_evidence()
        ev.physical_description = "500GB SSD"
        ev.digital_make = "Samsung"
        ev.digital_model = "860 EVO"
        ev.digital_serial_number = "SN123"
        ev.digital_storage_size = "500GB"
        ev.evidence_found = "Deleted files recovered"
        repo.add(ev)
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded.physical_description == "500GB SSD"
        assert loaded.digital_make == "Samsung"
        assert loaded.digital_model == "860 EVO"
        assert loaded.digital_serial_number == "SN123"
        assert loaded.evidence_found == "Deleted files recovered"


# ═══════════════════════════════════════════════════════════════════════════
# SQLiteNoteRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestSQLiteNoteRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        note = _make_note()
        repo.add(note)
        db.commit()
        loaded = repo.get_by_id("note-1")
        assert loaded is not None
        assert loaded.title == "Test Note"
        assert loaded.case_number == "C-001"

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _note_repo(tmp_path)
        assert repo.get_by_id("no-such-id") is None

    def test_get_all(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        repo.add(_make_note("n1", "C-001"))
        repo.add(_make_note("n2", "C-001"))
        db.commit()
        assert len(repo.get_all()) == 2

    def test_update(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        note = _make_note()
        repo.add(note)
        db.commit()
        note.update(title="Updated Title", body="Updated body", modified_by="bob")
        repo.update(note)
        db.commit()
        loaded = repo.get_by_id("note-1")
        assert loaded.title == "Updated Title"
        assert loaded.body == "Updated body"
        assert loaded.modified_by == "bob"

    def test_delete(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        note = _make_note()
        repo.add(note)
        db.commit()
        repo.delete("note-1")
        db.commit()
        assert repo.get_by_id("note-1") is None

    def test_exists(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        note = _make_note()
        repo.add(note)
        db.commit()
        assert repo.exists("note-1") is True
        assert repo.exists("no-such") is False


class TestSQLiteNoteRepositoryQueries:
    def test_get_for_case(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        repo.add(_make_note("n1", "C-001"))
        repo.add(_make_note("n2", "C-001"))
        repo.add(_make_note("n3", "C-002"))
        db.commit()
        results = repo.get_for_case("C-001")
        assert len(results) == 2
        assert all(n.case_number == "C-001" for n in results)

    def test_search_by_title(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        n1 = Note.create("n1", "C-001", "Malware Analysis", "trojans found", "alice")
        n2 = Note.create("n2", "C-001", "Network Logs", "traffic captured", "alice")
        repo.add(n1)
        repo.add(n2)
        db.commit()
        results = repo.search("malware")
        assert len(results) == 1
        assert results[0].title == "Malware Analysis"

    def test_search_by_body(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        n1 = Note.create("n1", "C-001", "Notes", "encrypted partitions found", "alice")
        n2 = Note.create("n2", "C-001", "Notes", "nothing interesting", "alice")
        repo.add(n1)
        repo.add(n2)
        db.commit()
        results = repo.search("encrypted")
        assert len(results) == 1

    def test_search_scoped_to_case(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        repo.add(Note.create("n1", "C-001", "keyword note", "", "alice"))
        repo.add(Note.create("n2", "C-002", "keyword note", "", "alice"))
        db.commit()
        results = repo.search("keyword", case_number="C-001")
        assert len(results) == 1
        assert results[0].id == "n1"

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        db, repo = _note_repo(tmp_path)
        repo.add(Note.create("n1", "C-001", "UPPERCASE TITLE", "body", "alice"))
        db.commit()
        results = repo.search("uppercase")
        assert len(results) == 1


# ═══════════════════════════════════════════════════════════════════════════
# UnitOfWork integration
# ═══════════════════════════════════════════════════════════════════════════

class TestUnitOfWorkEvidenceNoteWiring:
    def test_memory_provider_has_evidence_repo(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert uow.evidence is not None
        ev = _make_evidence()
        uow.evidence.add(ev)
        assert uow.evidence.get_by_id("1") is not None

    def test_memory_provider_has_notes_repo(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert uow.notes is not None
        note = _make_note()
        uow.notes.add(note)
        assert uow.notes.get_by_id("note-1") is not None

    def test_sqlite_provider_has_evidence_repo(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path, "uow_ev.db")
        uow = UnitOfWork(db_context=db, provider="sqlite")
        ev = _make_evidence()
        with uow:
            uow.evidence.add(ev)
        verify = SQLiteEvidenceRepository(db)
        loaded = verify.get_by_id("1")
        assert loaded is not None
        assert loaded.case_number == "C-001"

    def test_sqlite_provider_has_notes_repo(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path, "uow_notes.db")
        uow = UnitOfWork(db_context=db, provider="sqlite")
        note = _make_note()
        with uow:
            uow.notes.add(note)
        verify = SQLiteNoteRepository(db)
        loaded = verify.get_by_id("note-1")
        assert loaded is not None
        assert loaded.title == "Test Note"

    def test_custom_evidence_repo_override(self) -> None:
        from infrastructure.persistence.repositories.evidence_repository import InMemoryEvidenceRepository
        custom = InMemoryEvidenceRepository()
        uow = UnitOfWork(evidence_repo=custom)
        assert uow.evidence is custom

    def test_custom_note_repo_override(self) -> None:
        from infrastructure.persistence.repositories.note_repository import InMemoryNoteRepository
        custom = InMemoryNoteRepository()
        uow = UnitOfWork(note_repo=custom)
        assert uow.notes is custom
