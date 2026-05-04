"""domain/entities/notification.py — In-app notification entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.enums.notification_type import NotificationType


@dataclass
class Notification:
    """Represents a single notification for a user."""

    # ── Identity ─────────────────────────────────────────────────────────
    id: int
    notification_type: NotificationType
    recipient_username: str

    # ── Content ──────────────────────────────────────────────────────────
    title: str
    message: str

    # ── Associated entity ────────────────────────────────────────────────
    case_number: Optional[str] = None
    related_entity_id: Optional[str] = None   # Evidence ID, LegalProcess ID, etc.

    # ── State ────────────────────────────────────────────────────────────
    is_read: bool = False
    is_dismissed: bool = False

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(
        cls,
        id: int,
        notification_type: NotificationType,
        recipient_username: str,
        title: str,
        message: str,
        case_number: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> "Notification":
        return cls(
            id=id,
            notification_type=notification_type,
            recipient_username=recipient_username,
            title=title,
            message=message,
            case_number=case_number,
            related_entity_id=related_entity_id,
        )

    # ================================================================== #
    # State mutations                                                      #
    # ================================================================== #

    def mark_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def dismiss(self) -> None:
        if not self.is_dismissed:
            self.is_dismissed = True
            self.dismissed_at = datetime.utcnow()
            self.is_read = True
            if not self.read_at:
                self.read_at = datetime.utcnow()

    # ================================================================== #
    # Properties                                                           #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return str(self.id)

    @property
    def is_active(self) -> bool:
        return not self.is_dismissed

    def __repr__(self) -> str:
        return (
            f"Notification(id={self.id}, type={self.notification_type!r}, "
            f"read={self.is_read}, recipient={self.recipient_username!r})"
        )
