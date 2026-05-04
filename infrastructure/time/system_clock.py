"""infrastructure/time/system_clock.py - Production IClock implementation."""
from __future__ import annotations

from datetime import UTC, datetime

from application.interfaces.i_clock import IClock


class SystemClock(IClock):
    def utcnow(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def now_local(self) -> datetime:
        return datetime.now()
