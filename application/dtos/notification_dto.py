"""application/dtos/notification_dto.py — Notification data transfer objects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NotificationDto:
    """Read model for notifications."""

    notification_id: int
    notification_type: str
    recipient_username: str
    title: str
    message: str
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    read_at: Optional[datetime]
    case_number: Optional[str]
    related_entity_id: Optional[str]
