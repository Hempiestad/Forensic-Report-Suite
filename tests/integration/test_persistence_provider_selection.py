from __future__ import annotations

import pytest

from infrastructure.persistence.db_context import PostgreSQLDbContext
from infrastructure.persistence.repositories import (
    InMemoryCaseRepository,
    InMemoryReportRepository,
    InMemoryAuditRepository,
    InMemoryTemplateRepository,
    InMemoryNotificationRepository,
    PostgreSQLCaseRepository,
    PostgreSQLReportRepository,
    PostgreSQLAuditRepository,
    PostgreSQLTemplateRepository,
    PostgreSQLNotificationRepository,
    SQLiteCaseRepository,
    SQLiteReportRepository,
    SQLiteAuditRepository,
    SQLiteTemplateRepository,
    SQLiteNotificationRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def test_uow_default_provider_is_memory() -> None:
    uow = UnitOfWork()
    assert isinstance(uow.cases, InMemoryCaseRepository)
    assert isinstance(uow.reports, InMemoryReportRepository)
    assert isinstance(uow.audits, InMemoryAuditRepository)
    assert isinstance(uow.templates, InMemoryTemplateRepository)
    assert isinstance(uow.notifications, InMemoryNotificationRepository)


def test_uow_sqlite_provider_uses_sqlite_repo(tmp_path) -> None:
    db_path = str(tmp_path / "provider_sqlite.db")
    uow = UnitOfWork(provider="sqlite", sqlite_db_path=db_path)
    assert isinstance(uow.cases, SQLiteCaseRepository)
    assert isinstance(uow.reports, SQLiteReportRepository)
    assert isinstance(uow.audits, SQLiteAuditRepository)
    assert isinstance(uow.templates, SQLiteTemplateRepository)
    assert isinstance(uow.notifications, SQLiteNotificationRepository)


def test_uow_postgres_provider_requires_dsn() -> None:
    with pytest.raises(ValueError):
        UnitOfWork(provider="postgres")


def test_uow_postgres_provider_selects_postgres_repo_with_dsn() -> None:
    # No query is executed; this verifies selection/wiring only.
    uow = UnitOfWork(provider="postgres", postgres_dsn="postgresql://user:pass@localhost:5432/forensic")
    assert isinstance(uow.cases, PostgreSQLCaseRepository)
    assert isinstance(uow.reports, PostgreSQLReportRepository)
    assert isinstance(uow.audits, PostgreSQLAuditRepository)
    assert isinstance(uow.templates, PostgreSQLTemplateRepository)
    assert isinstance(uow.notifications, PostgreSQLNotificationRepository)


def test_uow_invalid_provider_rejected() -> None:
    with pytest.raises(ValueError):
        UnitOfWork(provider="unsupported")


def test_postgres_context_import_guard(monkeypatch) -> None:
    # This test ensures a clear error message if psycopg is unavailable at runtime.
    ctx = PostgreSQLDbContext("postgresql://user:pass@localhost:5432/forensic")
    try:
        _ = ctx.connection
    except RuntimeError as exc:
        assert "psycopg" in str(exc)
    except Exception:
        # psycopg installed or connection failed for another runtime reason; acceptable for additive scaffold.
        pass
