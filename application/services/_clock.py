"""Internal default clock adapter for application services."""
from __future__ import annotations

from datetime import UTC, datetime

from application.interfaces.i_clock import IClock


class DefaultClock(IClock):
    """System-backed clock implementation for service defaults."""

    def utcnow(self) -> datetime:
        # Keep naive UTC for compatibility with existing naive datetime fields.
        return datetime.now(UTC).replace(tzinfo=None)

    def now_local(self) -> datetime:
        return datetime.now()
