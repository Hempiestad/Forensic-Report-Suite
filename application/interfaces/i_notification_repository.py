"""application/interfaces/i_notification_repository.py - Typed notification repository contract."""
from __future__ import annotations

from abc import abstractmethod
from typing import List

from application.interfaces.i_repository import IRepository
from domain.entities.notification import Notification


class INotificationRepository(IRepository[Notification]):

    @abstractmethod
    def get_for_user(self, username: str, unread_only: bool = False) -> List[Notification]:
        """Return notifications for user."""

    @abstractmethod
    def get_unread_count(self, username: str) -> int:
        """Return unread count for user."""

    @abstractmethod
    def mark_all_as_read(self, username: str) -> int:
        """Mark all user notifications as read and return updated count."""
