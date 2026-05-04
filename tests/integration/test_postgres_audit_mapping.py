"""tests/integration/test_postgres_audit_mapping.py

Phase 3 continuation — PostgreSQL AuditEntry mapping tests.

These tests cover:
- `_to_entity` mapping behavior without a live DB
- details deserialisation behavior for dict/string/invalid payloads
- UnitOfWork provider selection for postgres audits
- Live CRUD smoke tests gated by FORENSIC_PG_DSN
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from domain.entities.audit_entry import AuditEntry
from infrastructure.persistence.repositories.postgres_audit_repository import (
    PostgreSQLAuditRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


def _row(**overrides) -> dict:
    base: dict = {
        "id": 1,
        "case_number": "AUD-PG-001",
        "event_type": "CASE_CREATED",
        "performed_by": "alice",
        "details": {"step": 1, "ok": True},
        "timestamp": datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        "previous_hash": "0" * 64,
        "entry_hash": "a" * 64,
    }
    base.update(overrides)
    return base


class TestPostgresAuditRepositoryMapping:
    def _repo(self) -> PostgreSQLAuditRepository:
        return PostgreSQLAuditRepository.__new__(PostgreSQLAuditRepository)

    def test_to_entity_basic_fields(self) -> None:
        repo = self._repo()
        entity = repo._to_entity(_row())
        assert isinstance(entity, AuditEntry)
        assert entity.id == 1
        assert entity.case_number == "AUD-PG-001"
        assert entity.event_type == "CASE_CREATED"
        assert entity.performed_by == "alice"

    def test_to_entity_preserves_hash_fields(self) -> None:
        repo = self._repo()
        entity = repo._to_entity(_row(previous_hash="b" * 64, entry_hash="c" * 64))
        assert entity.previous_hash == "b" * 64
        assert entity.entry_hash == "c" * 64

    def test_to_entity_details_dict_passthrough(self) -> None:
        repo = self._repo()
        details = {"nested": {"x": 1}, "list": [1, 2, 3]}
        entity = repo._to_entity(_row(details=details))
        assert entity.details == details

    def test_deserialise_details_from_json_string(self) -> None:
        repo = self._repo()
        entity = repo._to_entity(_row(details='{"k": "v", "n": 2}'))
        assert entity.details == {"k": "v", "n": 2}

    def test_deserialise_details_invalid_string_returns_empty(self) -> None:
        repo = self._repo()
        entity = repo._to_entity(_row(details="{not-json"))
        assert entity.details == {}

    def test_deserialise_details_none_returns_empty(self) -> None:
        repo = self._repo()
        entity = repo._to_entity(_row(details=None))
        assert entity.details == {}

    def test_to_entity_timestamp_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc)
        entity = repo._to_entity(_row(timestamp=ts))
        assert entity.timestamp == ts


class TestUnitOfWorkPostgresAuditProviderSelection:
    def test_memory_provider_uses_inmemory_audits(self) -> None:
        from infrastructure.persistence.repositories.audit_repository import InMemoryAuditRepository

        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.audits, InMemoryAuditRepository)

    @pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")
    def test_postgres_provider_uses_postgres_audits(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.audits, PostgreSQLAuditRepository)


@pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")
class TestPostgresLiveAuditCRUD:
    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_by_id(self) -> None:
        uow = self._uow()
        case_no = "PG-AUD-001"
        entry = AuditEntry.create(
            case_number=case_no,
            event_type="REPORT_EDITED",
            performed_by="auditor",
            details={"section": "summary", "chars": 120},
        )
        uow.audits.add(entry)
        uow.commit()

        loaded = uow.audits.get_by_id(str(entry.id))
        assert loaded is not None
        assert loaded.case_number == case_no
        assert loaded.event_type == "REPORT_EDITED"
        assert loaded.details["section"] == "summary"

        uow.audits.delete(str(entry.id))
        uow.commit()

    def test_get_for_case_and_last_entry(self) -> None:
        uow = self._uow()
        case_no = "PG-AUD-002"
        e1 = AuditEntry.create(case_number=case_no, event_type="CASE_CREATED", performed_by="auditor")
        e2 = AuditEntry.create(case_number=case_no, event_type="REPORT_SIGNED", performed_by="auditor")
        uow.audits.add(e1)
        uow.audits.add(e2)
        uow.commit()

        chain = uow.audits.get_for_case(case_no)
        assert len(chain) >= 2
        assert chain[-1].event_type in {"REPORT_SIGNED", "CASE_CREATED"}

        last = uow.audits.get_last_entry_for_case(case_no)
        assert last is not None

        uow.audits.delete(str(e1.id))
        uow.audits.delete(str(e2.id))
        uow.commit()
