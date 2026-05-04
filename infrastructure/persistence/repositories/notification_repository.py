"""infrastructure/persistence/repositories/notification_repository.py - Notification repository implementation."""
from __future__ import annotations

from typing import List, Optional

from application.interfaces.i_notification_repository import INotificationRepository
from domain.entities.notification import Notification


class InMemoryNotificationRepository(INotificationRepository):
    """In-memory notification repository for Phase 3 testing. Will be replaced with SQLite adapter."""

    def __init__(self) -> None:
        self._notifications: dict[str, Notification] = {}

    def get_by_id(self, entity_id: str) -> Optional[Notification]:
        return self._notifications.get(entity_id)

    def get_all(self) -> List[Notification]:
        return list(self._notifications.values())

    def add(self, entity: Notification) -> None:
        self._notifications[str(entity.id)] = entity

    def update(self, entity: Notification) -> None:
        self._notifications[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._notifications.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._notifications

    def get_for_user(self, username: str, unread_only: bool = False) -> List[Notification]:
        result = [n for n in self._notifications.values() if n.recipient_username == username]
        if unread_only:
            result = [n for n in result if not n.is_read]
        return result

    def get_unread_count(self, username: str) -> int:
        return sum(1 for n in self._notifications.values() if n.recipient_username == username and not n.is_read)

    def mark_all_as_read(self, username: str) -> int:
        count = 0
        for n in self._notifications.values():
            if n.recipient_username == username and not n.is_read:
                n.mark_read()
                count += 1
        return count
