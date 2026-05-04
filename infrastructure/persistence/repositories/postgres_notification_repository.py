"""PostgreSQL-backed notification repository implementation."""
from __future__ import annotations

from typing import List, Optional

from application.interfaces.i_notification_repository import INotificationRepository
from domain.entities.notification import Notification
from domain.enums.notification_type import NotificationType
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLNotificationRepository(INotificationRepository):
    """Concrete PostgreSQL adapter for notification persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Notification]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM notifications WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Notification]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM notifications ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Notification) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notifications (
                    id, notification_type, recipient_username, title, message,
                    case_number, related_entity_id, is_read, is_dismissed,
                    created_at, read_at, dismissed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entity.id,
                    entity.notification_type.value,
                    entity.recipient_username,
                    entity.title,
                    entity.message,
                    entity.case_number,
                    entity.related_entity_id,
                    entity.is_read,
                    entity.is_dismissed,
                    entity.created_at,
                    entity.read_at,
                    entity.dismissed_at,
                ),
            )

    def update(self, entity: Notification) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE notifications
                SET notification_type = %s,
                    recipient_username = %s,
                    title = %s,
                    message = %s,
                    case_number = %s,
                    related_entity_id = %s,
                    is_read = %s,
                    is_dismissed = %s,
                    created_at = %s,
                    read_at = %s,
                    dismissed_at = %s
                WHERE id = %s
                """,
                (
                    entity.notification_type.value,
                    entity.recipient_username,
                    entity.title,
                    entity.message,
                    entity.case_number,
                    entity.related_entity_id,
                    entity.is_read,
                    entity.is_dismissed,
                    entity.created_at,
                    entity.read_at,
                    entity.dismissed_at,
                    entity.id,
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM notifications WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM notifications WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    def get_for_user(self, username: str, unread_only: bool = False) -> List[Notification]:
        with self._db.connection.cursor() as cur:
            if unread_only:
                cur.execute(
                    "SELECT * FROM notifications WHERE recipient_username = %s AND is_read = FALSE ORDER BY created_at DESC, id DESC",
                    (username,),
                )
            else:
                cur.execute(
                    "SELECT * FROM notifications WHERE recipient_username = %s ORDER BY created_at DESC, id DESC",
                    (username,),
                )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_unread_count(self, username: str) -> int:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM notifications WHERE recipient_username = %s AND is_read = FALSE",
                (username,),
            )
            row = cur.fetchone()
        return int(row["c"] if row else 0)

    def mark_all_as_read(self, username: str) -> int:
        with self._db.connection.cursor() as cur:
            cur.execute(
                "UPDATE notifications SET is_read = TRUE, read_at = CURRENT_TIMESTAMP WHERE recipient_username = %s AND is_read = FALSE RETURNING id",
                (username,),
            )
            rows = cur.fetchall()
        return len(rows)

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
        notif.created_at = row["created_at"] or notif.created_at
        notif.read_at = row["read_at"]
        notif.dismissed_at = row["dismissed_at"]
        return notif

    @staticmethod
    def _parse_type(raw: str) -> NotificationType:
        try:
            return NotificationType(raw)
        except ValueError:
            return NotificationType.SYSTEM
