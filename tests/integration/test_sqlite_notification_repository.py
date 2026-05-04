"""tests/integration/test_sqlite_notification_repository.py

Integration tests for SQLiteNotificationRepository covering:
- Schema presence
- CRUD (add / get_by_id / update / delete / exists / get_all)
- get_for_user — all, unread_only flag
- get_unread_count
- mark_all_as_read
- NotificationType roundtrip for all enum members
- Boolean is_read / is_dismissed flag roundtrip
- Timestamps (read_at, dismissed_at) roundtrip
- UnitOfWork provider wiring
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from domain.entities.notification import Notification
from domain.enums.notification_type import NotificationType
from infrastructure.persistence.db_context import SQLiteDbContext
from infrastructure.persistence.repositories.notification_repository import InMemoryNotificationRepository
from infrastructure.persistence.repositories.sqlite_notification_repository import (
    SQLiteNotificationRepository,
)
from infrastructure.persistence.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path: Path) -> SQLiteDbContext:
    return SQLiteDbContext(str(tmp_path / "notifications.db"))


def _repo(tmp_path: Path) -> tuple[SQLiteDbContext, SQLiteNotificationRepository]:
    db = _ctx(tmp_path)
    return db, SQLiteNotificationRepository(db)


_ID = 0


def _notif(
    *,
    ntype: NotificationType = NotificationType.SYSTEM,
    recipient: str = "alice",
    title: str = "Test",
    message: str = "Test message",
    case_number: str | None = None,
    related_entity_id: str | None = None,
    id: int | None = None,
) -> Notification:
    global _ID
    _ID += 1
    return Notification.create(
        id=id if id is not None else _ID,
        notification_type=ntype,
        recipient_username=recipient,
        title=title,
        message=message,
        case_number=case_number,
        related_entity_id=related_entity_id,
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_notifications_table_exists(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'"
        ).fetchone()
        assert row is not None

    def test_schema_version_is_9(self, tmp_path: Path) -> None:
        db = _ctx(tmp_path)
        row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestSQLiteNotificationRepositoryCRUD:
    def test_add_and_get_by_id(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        n = _notif(id=1, ntype=NotificationType.CASE_CREATED, recipient="alice", title="Case Ready", message="A case is ready.")
        repo.add(n)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.recipient_username == "alice"
        assert loaded.notification_type == NotificationType.CASE_CREATED
        assert loaded.title == "Case Ready"
        assert loaded.message == "A case is ready."

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_by_id("99999") is None

    def test_get_all_returns_all_rows(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1, recipient="alice"))
        repo.add(_notif(id=2, recipient="bob"))
        db.commit()

        rows = repo.get_all()
        assert len(rows) == 2

    def test_update_persists_changes(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        n = _notif(id=1, title="Old Title")
        repo.add(n)
        db.commit()

        n.title = "New Title"
        n.is_read = True
        n.read_at = datetime.utcnow()
        repo.update(n)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.title == "New Title"
        assert loaded.is_read is True
        assert loaded.read_at is not None

    def test_delete_removes_row(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        n = _notif(id=1)
        repo.add(n)
        db.commit()

        repo.delete("1")
        db.commit()

        assert repo.get_by_id("1") is None
        assert not repo.exists("1")

    def test_exists_true_and_false(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=7))
        db.commit()

        assert repo.exists("7")
        assert not repo.exists("88")


# ---------------------------------------------------------------------------
# NotificationType roundtrip
# ---------------------------------------------------------------------------

class TestNotificationTypeRoundtrip:
    def test_all_types_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        for i, ntype in enumerate(NotificationType, start=1):
            repo.add(_notif(id=i, ntype=ntype))
        db.commit()

        for i, ntype in enumerate(NotificationType, start=1):
            loaded = repo.get_by_id(str(i))
            assert loaded is not None
            assert loaded.notification_type == ntype


# ---------------------------------------------------------------------------
# Boolean flags and timestamps
# ---------------------------------------------------------------------------

class TestBooleanAndTimestampRoundtrip:
    def test_is_read_false_default(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1))
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.is_read is False
        assert loaded.is_dismissed is False

    def test_is_dismissed_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        n = _notif(id=1)
        n.is_dismissed = True
        n.dismissed_at = datetime.utcnow()
        repo.add(n)
        db.commit()

        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.is_dismissed is True
        assert loaded.dismissed_at is not None

    def test_optional_fields_none(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1, case_number=None, related_entity_id=None))
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.case_number is None
        assert loaded.related_entity_id is None

    def test_case_number_and_entity_id_roundtrip(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1, case_number="C-LINK", related_entity_id="EV-42"))
        db.commit()
        loaded = repo.get_by_id("1")
        assert loaded is not None
        assert loaded.case_number == "C-LINK"
        assert loaded.related_entity_id == "EV-42"


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class TestSQLiteNotificationQueries:
    def test_get_for_user_all(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1, recipient="alice"))
        repo.add(_notif(id=2, recipient="alice"))
        repo.add(_notif(id=3, recipient="bob"))
        db.commit()

        rows = repo.get_for_user("alice")
        assert len(rows) == 2
        assert all(r.recipient_username == "alice" for r in rows)

    def test_get_for_user_unread_only(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        n_read = _notif(id=1, recipient="alice")
        n_read.is_read = True
        n_unread = _notif(id=2, recipient="alice")
        repo.add(n_read)
        repo.add(n_unread)
        db.commit()

        unread = repo.get_for_user("alice", unread_only=True)
        assert len(unread) == 1
        assert unread[0].id == 2

    def test_get_unread_count(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        n1 = _notif(id=1, recipient="alice")
        n2 = _notif(id=2, recipient="alice")
        n3 = _notif(id=3, recipient="alice")
        n3.is_read = True
        repo.add(n1)
        repo.add(n2)
        repo.add(n3)
        db.commit()

        assert repo.get_unread_count("alice") == 2

    def test_get_unread_count_zero_for_new_user(self, tmp_path: Path) -> None:
        _, repo = _repo(tmp_path)
        assert repo.get_unread_count("nobody") == 0

    def test_mark_all_as_read_updates_count(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1, recipient="alice"))
        repo.add(_notif(id=2, recipient="alice"))
        repo.add(_notif(id=3, recipient="bob"))
        db.commit()

        updated = repo.mark_all_as_read("alice")
        db.commit()

        assert updated == 2
        assert repo.get_unread_count("alice") == 0
        # Bob's notification remains unread
        assert repo.get_unread_count("bob") == 1

    def test_mark_all_as_read_idempotent(self, tmp_path: Path) -> None:
        db, repo = _repo(tmp_path)
        repo.add(_notif(id=1, recipient="alice"))
        db.commit()

        repo.mark_all_as_read("alice")
        db.commit()
        second_pass = repo.mark_all_as_read("alice")
        db.commit()

        assert second_pass == 0


# ---------------------------------------------------------------------------
# UnitOfWork wiring
# ---------------------------------------------------------------------------

class TestUnitOfWorkNotificationWiring:
    def test_memory_provider_uses_inmemory_notifications(self) -> None:
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.notifications, InMemoryNotificationRepository)

    def test_sqlite_provider_uses_sqlite_notifications(self, tmp_path: Path) -> None:
        uow = UnitOfWork(provider="sqlite", sqlite_db_path=str(tmp_path / "uow.db"))
        assert isinstance(uow.notifications, SQLiteNotificationRepository)

    def test_custom_notification_repo_override(self) -> None:
        custom = InMemoryNotificationRepository()
        uow = UnitOfWork(provider="memory", notification_repo=custom)
        assert uow.notifications is custom
