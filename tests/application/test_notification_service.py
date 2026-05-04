from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from application.interfaces.i_notification_repository import INotificationRepository
from application.services.notification_service import NotificationService
from domain.entities.notification import Notification
from domain.enums.notification_type import NotificationType


class InMemoryNotificationRepository(INotificationRepository):
    def __init__(self) -> None:
        self._items: Dict[str, Notification] = {}
        self._next_id = 1

    def get_by_id(self, entity_id: str) -> Optional[Notification]:
        return self._items.get(entity_id)

    def get_all(self) -> List[Notification]:
        return list(self._items.values())

    def add(self, entity: Notification) -> None:
        self._items[str(entity.id)] = entity

    def update(self, entity: Notification) -> None:
        self._items[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._items.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._items

    def get_for_user(self, username: str, unread_only: bool = False) -> List[Notification]:
        result = [n for n in self._items.values() if n.recipient_username == username]
        if unread_only:
            return [n for n in result if not n.is_read]
        return result

    def get_unread_count(self, username: str) -> int:
        return sum(1 for n in self._items.values() if n.recipient_username == username and not n.is_read)

    def mark_all_as_read(self, username: str) -> int:
        count = 0
        for n in self._items.values():
            if n.recipient_username == username and not n.is_read:
                n.mark_read()
                count += 1
        return count


@pytest.fixture
def notification_service() -> NotificationService:
    return NotificationService(InMemoryNotificationRepository())  # type: ignore[arg-type]


def test_create_notification(notification_service: NotificationService) -> None:
    notif = notification_service.create_notification(
        notification_type=NotificationType.CASE_CREATED,
        recipient_username="det.smith",
        title="New Case",
        message="CASE-600 has been created",
        case_number="CASE-600",
    )

    assert notif.recipient_username == "det.smith"
    assert notif.title == "New Case"
    assert notif.is_read is False


def test_notifications_for_user(notification_service: NotificationService) -> None:
    notification_service.create_notification(
        notification_type=NotificationType.CASE_CREATED,
        recipient_username="det.smith",
        title="Case 1",
        message="msg1",
    )
    notification_service.create_notification(
        notification_type=NotificationType.CASE_CREATED,
        recipient_username="det.jones",
        title="Case 2",
        message="msg2",
    )

    smith_notifs = notification_service.get_notifications_for_user("det.smith")
    assert len(smith_notifs) == 1
    assert smith_notifs[0].recipient_username == "det.smith"

    jones_notifs = notification_service.get_notifications_for_user("det.jones")
    assert len(jones_notifs) == 1


def test_mark_as_read(notification_service: NotificationService) -> None:
    notif = notification_service.create_notification(
        notification_type=NotificationType.CASE_CREATED,
        recipient_username="det.smith",
        title="Test",
        message="test",
    )

    assert notification_service.get_unread_count("det.smith") == 1
    notification_service.mark_as_read(notif.notification_id)
    assert notification_service.get_unread_count("det.smith") == 0


def test_dismiss_notification(notification_service: NotificationService) -> None:
    notif = notification_service.create_notification(
        notification_type=NotificationType.COURT_DATE_REMINDER,
        recipient_username="det.smith",
        title="Court Date",
        message="upcoming",
    )

    notification_service.dismiss(notif.notification_id)
    fetched = notification_service.get_notifications_for_user("det.smith", unread_only=False)
    assert len(fetched) == 1
    assert fetched[0].is_dismissed is True


def test_mark_all_as_read(notification_service: NotificationService) -> None:
    notification_service.create_notification(
        NotificationType.CASE_CREATED, "det.smith", "n1", "msg1"
    )
    notification_service.create_notification(
        NotificationType.CASE_CREATED, "det.smith", "n2", "msg2"
    )

    assert notification_service.get_unread_count("det.smith") == 2
    notification_service.mark_all_as_read("det.smith")
    assert notification_service.get_unread_count("det.smith") == 0
