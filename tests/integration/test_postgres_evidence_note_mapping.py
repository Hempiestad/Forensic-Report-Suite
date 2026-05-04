"""tests/integration/test_postgres_evidence_note_mapping.py

Phase 8 — PostgreSQL Evidence and Note repository mapping tests.

These tests exercise `_to_entity` mapping logic and UnitOfWork provider
selection without requiring a live PostgreSQL connection.  Live-DB tests
are gated by the FORENSIC_PG_DSN environment variable.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import pytest

from domain.entities.evidence import Evidence
from domain.entities.note import Note
from domain.enums.evidence_status import EvidenceStatus
from infrastructure.persistence.repositories.postgres_evidence_repository import (
    PostgreSQLEvidenceRepository,
)
from infrastructure.persistence.repositories.postgres_note_repository import (
    PostgreSQLNoteRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


def _ev_row(**overrides) -> dict:
    """Return a minimal evidence row dict as psycopg2 would produce."""
    base: dict = {
        "id": 1,
        "case_number": "EV-CASE-001",
        "evidence_item_number": "EV-001",
        "item_type": "Digital",
        "physical_description": None,
        "digital_make": "Apple",
        "digital_model": "iPhone 14",
        "digital_type": "Mobile",
        "digital_serial_number": "SN-ABC123",
        "digital_storage_size": "256GB",
        "password": None,
        "status": "not_imaged",
        "imaged_date": None,
        "analyzed_date": None,
        "completed_date": None,
        "evidence_found": None,
        "created_at": datetime(2026, 1, 1, 10, 0, 0),
        "modified_at": datetime(2026, 1, 1, 10, 0, 0),
    }
    base.update(overrides)
    return base


def _note_row(**overrides) -> dict:
    """Return a minimal note row dict as psycopg2 would produce."""
    base: dict = {
        "id": str(uuid.uuid4()),
        "case_number": "NOTE-CASE-001",
        "title": "Examination Notes",
        "body": "Device was powered off on arrival.",
        "created_by": "examiner1",
        "created_at": datetime(2026, 2, 1, 9, 0, 0),
        "modified_at": None,
        "modified_by": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# PostgreSQLEvidenceRepository — _to_entity mapping
# ---------------------------------------------------------------------------

class TestPostgreSQLEvidenceRepositoryMapping:
    """Unit tests for row → Evidence entity mapping (no DB required)."""

    def _repo(self) -> PostgreSQLEvidenceRepository:
        return PostgreSQLEvidenceRepository.__new__(PostgreSQLEvidenceRepository)

    def test_to_entity_basic_fields(self) -> None:
        repo = self._repo()
        row = _ev_row()
        ev = repo._to_entity(row)
        assert ev.id == 1
        assert ev.case_number == "EV-CASE-001"
        assert ev.evidence_item_number == "EV-001"
        assert ev.item_type == "Digital"

    def test_to_entity_status_enum(self) -> None:
        repo = self._repo()
        ev = repo._to_entity(_ev_row(status="imaging_in_progress"))
        assert ev.status == EvidenceStatus.IMAGING_IN_PROGRESS

    def test_to_entity_all_statuses(self) -> None:
        repo = self._repo()
        for status in EvidenceStatus:
            ev = repo._to_entity(_ev_row(status=status.value))
            assert ev.status == status

    def test_to_entity_datetime_objects_passed_through(self) -> None:
        """psycopg2 returns datetime objects; _to_entity should accept them."""
        repo = self._repo()
        imaged = datetime(2026, 3, 15, 8, 30)
        ev = repo._to_entity(_ev_row(imaged_date=imaged))
        assert ev.imaged_date == imaged

    def test_to_entity_none_dates_remain_none(self) -> None:
        repo = self._repo()
        ev = repo._to_entity(_ev_row(imaged_date=None, analyzed_date=None, completed_date=None))
        assert ev.imaged_date is None
        assert ev.analyzed_date is None
        assert ev.completed_date is None

    def test_to_entity_optional_digital_fields(self) -> None:
        repo = self._repo()
        ev = repo._to_entity(
            _ev_row(digital_make=None, digital_model=None, digital_serial_number=None)
        )
        assert ev.digital_make is None
        assert ev.digital_model is None
        assert ev.digital_serial_number is None

    def test_to_entity_iso_string_dates_parsed(self) -> None:
        """Fallback: accept ISO strings in case of string-returning adapters."""
        repo = self._repo()
        iso = "2026-04-01T12:00:00"
        ev = repo._to_entity(_ev_row(imaged_date=iso))
        assert ev.imaged_date == datetime(2026, 4, 1, 12, 0, 0)

    def test_parse_dt_none_returns_none(self) -> None:
        assert PostgreSQLEvidenceRepository._parse_dt(None) is None

    def test_parse_dt_datetime_passthrough(self) -> None:
        dt = datetime(2026, 6, 15)
        assert PostgreSQLEvidenceRepository._parse_dt(dt) is dt

    def test_parse_dt_invalid_string_returns_none(self) -> None:
        assert PostgreSQLEvidenceRepository._parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# PostgreSQLNoteRepository — _to_entity mapping
# ---------------------------------------------------------------------------

class TestPostgreSQLNoteRepositoryMapping:
    """Unit tests for row → Note entity mapping (no DB required)."""

    def _repo(self) -> PostgreSQLNoteRepository:
        return PostgreSQLNoteRepository.__new__(PostgreSQLNoteRepository)

    def test_to_entity_basic_fields(self) -> None:
        repo = self._repo()
        row = _note_row()
        note = repo._to_entity(row)
        assert note.case_number == "NOTE-CASE-001"
        assert note.title == "Examination Notes"
        assert note.body == "Device was powered off on arrival."
        assert note.created_by == "examiner1"

    def test_to_entity_id_is_string(self) -> None:
        repo = self._repo()
        nid = str(uuid.uuid4())
        note = repo._to_entity(_note_row(id=nid))
        assert note.id == nid

    def test_to_entity_modified_at_none(self) -> None:
        repo = self._repo()
        note = repo._to_entity(_note_row(modified_at=None, modified_by=None))
        assert note.modified_at is None
        assert note.modified_by is None

    def test_to_entity_modified_at_datetime(self) -> None:
        repo = self._repo()
        mod = datetime(2026, 5, 1)
        note = repo._to_entity(_note_row(modified_at=mod, modified_by="reviewer"))
        assert note.modified_at == mod
        assert note.modified_by == "reviewer"

    def test_to_entity_body_none_becomes_empty_string(self) -> None:
        repo = self._repo()
        note = repo._to_entity(_note_row(body=None))
        assert note.body == ""

    def test_to_entity_created_at_datetime_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 1, 15, 8, 0, 0)
        note = repo._to_entity(_note_row(created_at=ts))
        assert note.created_at == ts

    def test_to_entity_created_at_iso_string_parsed(self) -> None:
        repo = self._repo()
        note = repo._to_entity(_note_row(created_at="2026-03-10T14:00:00"))
        assert note.created_at == datetime(2026, 3, 10, 14, 0, 0)

    def test_parse_dt_none_returns_none(self) -> None:
        assert PostgreSQLNoteRepository._parse_dt(None) is None

    def test_parse_dt_datetime_passthrough(self) -> None:
        dt = datetime(2026, 6, 15)
        assert PostgreSQLNoteRepository._parse_dt(dt) is dt

    def test_parse_dt_invalid_string_returns_none(self) -> None:
        assert PostgreSQLNoteRepository._parse_dt("bad-date") is None


# ---------------------------------------------------------------------------
# UnitOfWork — provider selection for Evidence and Note
# ---------------------------------------------------------------------------

class TestUnitOfWorkPostgresEvidenceNoteProviderSelection:
    """Verify UoW wires correct repos for postgres/memory/override."""

    def test_memory_provider_uses_in_memory_evidence(self) -> None:
        from infrastructure.persistence.repositories.evidence_repository import (
            InMemoryEvidenceRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.evidence, InMemoryEvidenceRepository)

    def test_memory_provider_uses_in_memory_notes(self) -> None:
        from infrastructure.persistence.repositories.note_repository import (
            InMemoryNoteRepository,
        )
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.notes, InMemoryNoteRepository)

    def test_custom_evidence_repo_override(self) -> None:
        from infrastructure.persistence.repositories.evidence_repository import (
            InMemoryEvidenceRepository,
        )
        custom = InMemoryEvidenceRepository()
        uow = UnitOfWork(provider="memory", evidence_repo=custom)
        assert uow.evidence is custom

    def test_custom_note_repo_override(self) -> None:
        from infrastructure.persistence.repositories.note_repository import (
            InMemoryNoteRepository,
        )
        custom = InMemoryNoteRepository()
        uow = UnitOfWork(provider="memory", note_repo=custom)
        assert uow.notes is custom

    def test_sqlite_provider_uses_sqlite_evidence(self) -> None:
        import tempfile, os
        from infrastructure.persistence.repositories.sqlite_evidence_repository import (
            SQLiteEvidenceRepository,
        )
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            uow = UnitOfWork(provider="sqlite", sqlite_db_path=db_path)
            assert isinstance(uow.evidence, SQLiteEvidenceRepository)
        finally:
            os.unlink(db_path)

    def test_sqlite_provider_uses_sqlite_notes(self) -> None:
        import tempfile, os
        from infrastructure.persistence.repositories.sqlite_note_repository import (
            SQLiteNoteRepository,
        )
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            uow = UnitOfWork(provider="sqlite", sqlite_db_path=db_path)
            assert isinstance(uow.notes, SQLiteNoteRepository)
        finally:
            os.unlink(db_path)

    @pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")
    def test_postgres_provider_uses_postgres_evidence(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.evidence, PostgreSQLEvidenceRepository)

    @pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")
    def test_postgres_provider_uses_postgres_notes(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.notes, PostgreSQLNoteRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (skipped unless FORENSIC_PG_DSN is set)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")
class TestPostgresLiveEvidenceCRUD:
    """Full CRUD round-trip against a live PostgreSQL instance."""

    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_evidence(self) -> None:
        uow = self._uow()
        ev = Evidence.create(
            id=9900,
            case_number=f"PG-EV-{uuid.uuid4().hex[:8]}",
            evidence_item_number="EV-PG-001",
            item_type="Digital",
        )
        uow.evidence.add(ev)
        uow.commit()

        loaded = uow.evidence.get_by_id(str(ev.id))
        assert loaded is not None
        assert loaded.evidence_item_number == "EV-PG-001"

        uow.evidence.delete(str(ev.id))
        uow.commit()

    def test_evidence_roundtrip_all_fields(self) -> None:
        uow = self._uow()
        now = datetime.utcnow().replace(microsecond=0)
        ev = Evidence(
            id=9901,
            case_number=f"PG-EV-{uuid.uuid4().hex[:8]}",
            evidence_item_number="EV-PG-002",
            item_type="Physical",
            physical_description="Black laptop bag",
            digital_make="Dell",
            digital_model="XPS 15",
            digital_type="Laptop",
            digital_serial_number="DELL-SN-9999",
            digital_storage_size="512GB",
            password="s3cr3t",
            status=EvidenceStatus.IMAGED,
            imaged_date=now,
            evidence_found="Deleted photos recovered",
            created_at=now,
            modified_at=now,
        )
        uow.evidence.add(ev)
        uow.commit()

        loaded = uow.evidence.get_by_id("9901")
        assert loaded is not None
        assert loaded.digital_model == "XPS 15"
        assert loaded.status == EvidenceStatus.IMAGED
        assert loaded.imaged_date is not None

        uow.evidence.delete("9901")
        uow.commit()


@pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")
class TestPostgresLiveNoteCRUD:
    """Full CRUD round-trip for Note against a live PostgreSQL instance."""

    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_note(self) -> None:
        uow = self._uow()
        note = Note.create(
            id=str(uuid.uuid4()),
            case_number=f"PG-NOTE-{uuid.uuid4().hex[:8]}",
            title="First observation",
            body="Device was in a locked state.",
            created_by="examiner",
        )
        uow.notes.add(note)
        uow.commit()

        loaded = uow.notes.get_by_id(note.id)
        assert loaded is not None
        assert loaded.title == "First observation"

        uow.notes.delete(note.id)
        uow.commit()

    def test_note_search_ilike(self) -> None:
        uow = self._uow()
        case_no = f"PG-NOTE-{uuid.uuid4().hex[:8]}"
        n1 = Note.create(str(uuid.uuid4()), case_no, "Forensic Analysis", "Found artifacts.", "examiner")
        n2 = Note.create(str(uuid.uuid4()), case_no, "Chain of Custody", "Item logged.", "examiner")
        uow.notes.add(n1)
        uow.notes.add(n2)
        uow.commit()

        results = uow.notes.search("forensic", case_number=case_no)
        assert len(results) == 1
        assert results[0].id == n1.id

        uow.notes.delete(n1.id)
        uow.notes.delete(n2.id)
        uow.commit()
