"""tests/integration/test_postgres_notification_mapping.py

PostgreSQL Notification repository: mapping tests (no live DB required),
_parse_type helper, UnitOfWork provider selection. Live tests gated by
FORENSIC_PG_DSN.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from domain.entities.notification import Notification
from domain.enums.notification_type import NotificationType
from infrastructure.persistence.repositories.postgres_notification_repository import (
    PostgreSQLNotificationRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


def _pg_dsn() -> str | None:
    return os.getenv("FORENSIC_PG_DSN")


_skip_pg = pytest.mark.skipif(not _pg_dsn(), reason="FORENSIC_PG_DSN not set")


def _row(**overrides) -> dict:
    base: dict = {
        "id": 1,
        "notification_type": "system",
        "recipient_username": "alice",
        "title": "Test Notification",
        "message": "Something happened.",
        "case_number": None,
        "related_entity_id": None,
        "is_read": False,
        "is_dismissed": False,
        "created_at": datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc),
        "read_at": None,
        "dismissed_at": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _to_entity mapping (no live DB)
# ---------------------------------------------------------------------------

class TestPostgresNotificationMapping:
    def _repo(self) -> PostgreSQLNotificationRepository:
        return PostgreSQLNotificationRepository.__new__(PostgreSQLNotificationRepository)

    def test_basic_fields(self) -> None:
        repo = self._repo()
        n = repo._to_entity(_row())
        assert isinstance(n, Notification)
        assert n.id == 1
        assert n.recipient_username == "alice"
        assert n.title == "Test Notification"
        assert n.message == "Something happened."
        assert n.notification_type == NotificationType.SYSTEM

    def test_is_read_false(self) -> None:
        repo = self._repo()
        n = repo._to_entity(_row(is_read=False))
        assert n.is_read is False

    def test_is_read_true(self) -> None:
        repo = self._repo()
        n = repo._to_entity(_row(is_read=True))
        assert n.is_read is True

    def test_is_dismissed_true(self) -> None:
        repo = self._repo()
        n = repo._to_entity(_row(is_dismissed=True))
        assert n.is_dismissed is True

    def test_read_at_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 5, 1, tzinfo=timezone.utc)
        n = repo._to_entity(_row(is_read=True, read_at=ts))
        assert n.read_at == ts

    def test_dismissed_at_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 5, 2, tzinfo=timezone.utc)
        n = repo._to_entity(_row(is_dismissed=True, dismissed_at=ts))
        assert n.dismissed_at == ts

    def test_case_number_and_entity_id(self) -> None:
        repo = self._repo()
        n = repo._to_entity(_row(case_number="C-99", related_entity_id="LP-55"))
        assert n.case_number == "C-99"
        assert n.related_entity_id == "LP-55"

    def test_optional_nulls_remain_none(self) -> None:
        repo = self._repo()
        n = repo._to_entity(_row(case_number=None, related_entity_id=None, read_at=None, dismissed_at=None))
        assert n.case_number is None
        assert n.related_entity_id is None
        assert n.read_at is None
        assert n.dismissed_at is None

    def test_created_at_passthrough(self) -> None:
        repo = self._repo()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        n = repo._to_entity(_row(created_at=ts))
        assert n.created_at == ts


# ---------------------------------------------------------------------------
# _parse_type static helper
# ---------------------------------------------------------------------------

class TestParseNotificationType:
    def test_all_valid_values(self) -> None:
        for ntype in NotificationType:
            assert PostgreSQLNotificationRepository._parse_type(ntype.value) == ntype

    def test_unknown_falls_back_to_system(self) -> None:
        assert PostgreSQLNotificationRepository._parse_type("totally_unknown") == NotificationType.SYSTEM

    def test_empty_string_falls_back_to_system(self) -> None:
        assert PostgreSQLNotificationRepository._parse_type("") == NotificationType.SYSTEM


# ---------------------------------------------------------------------------
# UnitOfWork provider selection
# ---------------------------------------------------------------------------

class TestUoWPostgresNotificationProviderSelection:
    def test_memory_provider_uses_inmemory(self) -> None:
        from infrastructure.persistence.repositories.notification_repository import InMemoryNotificationRepository
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.notifications, InMemoryNotificationRepository)

    def test_sqlite_provider_uses_sqlite(self, tmp_path) -> None:
        from infrastructure.persistence.repositories.sqlite_notification_repository import SQLiteNotificationRepository
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "notif.db"))
        assert isinstance(uow.notifications, SQLiteNotificationRepository)

    @_skip_pg
    def test_postgres_provider_uses_postgres(self) -> None:
        uow = UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())
        assert isinstance(uow.notifications, PostgreSQLNotificationRepository)


# ---------------------------------------------------------------------------
# Live PostgreSQL tests (gated by FORENSIC_PG_DSN)
# ---------------------------------------------------------------------------

@_skip_pg
class TestPostgresLiveNotificationCRUD:
    def _uow(self) -> UnitOfWork:
        return UnitOfWork(provider="postgres", postgres_dsn=_pg_dsn())

    def test_add_and_get_by_id(self) -> None:
        uow = self._uow()
        n = Notification.create(
            id=98901,
            notification_type=NotificationType.CASE_ASSIGNED,
            recipient_username="pg_tester",
            title="Case Assigned",
            message="You have been assigned to case PG-001.",
            case_number="PG-001",
        )
        try:
            uow.notifications.add(n)
            uow.commit()
            loaded = uow.notifications.get_by_id("98901")
            assert loaded is not None
            assert loaded.notification_type == NotificationType.CASE_ASSIGNED
            assert loaded.recipient_username == "pg_tester"
        finally:
            uow.notifications.delete("98901")
            uow.commit()

    def test_get_for_user_and_unread_count(self) -> None:
        uow = self._uow()
        n1 = Notification.create(id=98902, notification_type=NotificationType.SYSTEM,
                                  recipient_username="pg_user2", title="N1", message="M1")
        n2 = Notification.create(id=98903, notification_type=NotificationType.SYSTEM,
                                  recipient_username="pg_user2", title="N2", message="M2")
        try:
            uow.notifications.add(n1)
            uow.notifications.add(n2)
            uow.commit()

            assert uow.notifications.get_unread_count("pg_user2") == 2

            updated = uow.notifications.mark_all_as_read("pg_user2")
            uow.commit()
            assert updated == 2
            assert uow.notifications.get_unread_count("pg_user2") == 0
        finally:
            uow.notifications.delete("98902")
            uow.notifications.delete("98903")
            uow.commit()
