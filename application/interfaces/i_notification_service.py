"""application/interfaces/i_notification_service.py — Notification service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.enums.notification_type import NotificationType


class INotificationService(ABC):

    @abstractmethod
    def create_notification(
        self,
        notification_type: NotificationType,
        recipient_username: str,
        title: str,
        message: str,
        case_number: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> object:
        """Create and persist a new notification. Returns NotificationDto."""

    @abstractmethod
    def get_notifications_for_user(self, username: str, unread_only: bool = False) -> List[object]:
        """Return notification list for a user."""

    @abstractmethod
    def get_unread_count(self, username: str) -> int:
        """Return count of unread notifications."""

    @abstractmethod
    def mark_as_read(self, notification_id: int) -> None:
        """Mark a single notification as read."""

    @abstractmethod
    def mark_all_as_read(self, username: str) -> None:
        """Mark all of a user's notifications as read."""

    @abstractmethod
    def dismiss(self, notification_id: int) -> None:
        """Dismiss (hide) a notification."""

    @abstractmethod
    def check_and_create_court_date_reminders(self, days_ahead: int = 7) -> int:
        """
        Check for upcoming court dates and create reminder notifications.
        Returns number of notifications created.
        """

    @abstractmethod
    def check_and_create_overdue_legal_process_alerts(self) -> int:
        """
        Check for overdue legal processes and create alert notifications.
        Returns number of notifications created.
        """
