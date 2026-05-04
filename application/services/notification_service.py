"""application/services/notification_service.py - Notification service scaffold."""
from __future__ import annotations

from typing import List, Optional

from application.dtos.notification_dto import NotificationDto
from application.interfaces.i_clock import IClock
from application.interfaces.i_notification_repository import INotificationRepository
from application.interfaces.i_notification_service import INotificationService
from application.services._clock import DefaultClock
from domain.entities.notification import Notification
from domain.enums.notification_type import NotificationType
from domain.exceptions.domain_exceptions import EntityNotFoundError


class NotificationService(INotificationService):
    """Application service for in-app notifications."""

    def __init__(self, notification_repository: INotificationRepository, clock: Optional[IClock] = None) -> None:
        self._notifications = notification_repository
        self._clock = clock or DefaultClock()

    def create_notification(
        self,
        notification_type: NotificationType,
        recipient_username: str,
        title: str,
        message: str,
        case_number: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> NotificationDto:
        next_id = self._next_id()
        notification = Notification.create(
            id=next_id,
            notification_type=notification_type,
            recipient_username=recipient_username,
            title=title,
            message=message,
            case_number=case_number,
            related_entity_id=related_entity_id,
        )
        notification.created_at = self._clock.utcnow()
        self._notifications.add(notification)
        return self._to_dto(notification)

    def get_notifications_for_user(self, username: str, unread_only: bool = False) -> List[NotificationDto]:
        entries = self._notifications.get_for_user(username, unread_only=unread_only)
        return [self._to_dto(n) for n in entries]

    def get_unread_count(self, username: str) -> int:
        return self._notifications.get_unread_count(username)

    def mark_as_read(self, notification_id: int) -> None:
        notification = self._require(notification_id)
        notification.mark_read()
        self._notifications.update(notification)

    def mark_all_as_read(self, username: str) -> None:
        updated = self._notifications.mark_all_as_read(username)
        if updated == 0:
            return

    def dismiss(self, notification_id: int) -> None:
        notification = self._require(notification_id)
        notification.dismiss()
        self._notifications.update(notification)

    def check_and_create_court_date_reminders(self, days_ahead: int = 7) -> int:
        # Placeholder hook for Phase 6 integration with court-date projections.
        return 0

    def check_and_create_overdue_legal_process_alerts(self) -> int:
        # Placeholder hook for Phase 6 integration with legal workflow projections.
        return 0

    def _require(self, notification_id: int) -> Notification:
        entity = self._notifications.get_by_id(str(notification_id))
        if entity is None:
            raise EntityNotFoundError("Notification", notification_id)
        return entity

    def _next_id(self) -> int:
        items = self._notifications.get_all()
        if not items:
            return 1
        return max(i.id for i in items) + 1

    @staticmethod
    def _to_dto(notification: Notification) -> NotificationDto:
        return NotificationDto(
            notification_id=notification.id,
            notification_type=str(notification.notification_type),
            recipient_username=notification.recipient_username,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            is_dismissed=notification.is_dismissed,
            created_at=notification.created_at,
            read_at=notification.read_at,
            case_number=notification.case_number,
            related_entity_id=notification.related_entity_id,
        )
