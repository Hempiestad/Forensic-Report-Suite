"""SQLite-backed notification repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_notification_repository import INotificationRepository
from domain.entities.notification import Notification
from domain.enums.notification_type import NotificationType
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteNotificationRepository(INotificationRepository):
    """Concrete SQLite adapter for notification persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Notification]:
        row = self._db.connection.execute("SELECT * FROM notifications WHERE id = ?", (int(entity_id),)).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Notification]:
        rows = self._db.connection.execute("SELECT * FROM notifications ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Notification) -> None:
        self._db.connection.execute(
            """
            INSERT INTO notifications (
                id, notification_type, recipient_username, title, message,
                case_number, related_entity_id, is_read, is_dismissed,
                created_at, read_at, dismissed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.id,
                entity.notification_type.value,
                entity.recipient_username,
                entity.title,
                entity.message,
                entity.case_number,
                entity.related_entity_id,
                1 if entity.is_read else 0,
                1 if entity.is_dismissed else 0,
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                self._dt_to_iso(entity.read_at),
                self._dt_to_iso(entity.dismissed_at),
            ),
        )

    def update(self, entity: Notification) -> None:
        self._db.connection.execute(
            """
            UPDATE notifications
            SET notification_type = ?, recipient_username = ?, title = ?, message = ?,
                case_number = ?, related_entity_id = ?, is_read = ?, is_dismissed = ?,
                created_at = ?, read_at = ?, dismissed_at = ?
            WHERE id = ?
            """,
            (
                entity.notification_type.value,
                entity.recipient_username,
                entity.title,
                entity.message,
                entity.case_number,
                entity.related_entity_id,
                1 if entity.is_read else 0,
                1 if entity.is_dismissed else 0,
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                self._dt_to_iso(entity.read_at),
                self._dt_to_iso(entity.dismissed_at),
                entity.id,
            ),
        )

    def delete(self, entity_id: str) -> None:
        self._db.connection.execute("DELETE FROM notifications WHERE id = ?", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute("SELECT 1 FROM notifications WHERE id = ? LIMIT 1", (int(entity_id),)).fetchone()
        return row is not None

    def get_for_user(self, username: str, unread_only: bool = False) -> List[Notification]:
        if unread_only:
            rows = self._db.connection.execute(
                "SELECT * FROM notifications WHERE recipient_username = ? AND is_read = 0 ORDER BY created_at DESC, id DESC",
                (username,),
            ).fetchall()
        else:
            rows = self._db.connection.execute(
                "SELECT * FROM notifications WHERE recipient_username = ? ORDER BY created_at DESC, id DESC",
                (username,),
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_unread_count(self, username: str) -> int:
        row = self._db.connection.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE recipient_username = ? AND is_read = 0",
            (username,),
        ).fetchone()
        return int(row["c"] if row else 0)

    def mark_all_as_read(self, username: str) -> int:
        cursor = self._db.connection.execute(
            "UPDATE notifications SET is_read = 1, read_at = ? WHERE recipient_username = ? AND is_read = 0",
            (datetime.utcnow().isoformat(), username),
        )
        return int(cursor.rowcount if cursor.rowcount is not None else 0)

    def _to_entity(self, row) -> Notification:
        notif = Notification.create(
            id=int(row["id"]),
            notification_type=self._parse_type(row["notification_type"]),
            recipient_username=row["recipient_username"],
            title=row["title"],
            message=row["message"],
            case_number=row["case_number"],
            related_entity_id=row["related_entity_id"],
        )
        notif.is_read = bool(row["is_read"])
        notif.is_dismissed = bool(row["is_dismissed"])
        notif.created_at = self._iso_to_dt(row["created_at"]) or notif.created_at
        notif.read_at = self._iso_to_dt(row["read_at"])
        notif.dismissed_at = self._iso_to_dt(row["dismissed_at"])
        return notif

    @staticmethod
    def _parse_type(raw: str) -> NotificationType:
        try:
            return NotificationType(raw)
        except ValueError:
            return NotificationType.SYSTEM

    @staticmethod
    def _dt_to_iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @staticmethod
    def _iso_to_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
