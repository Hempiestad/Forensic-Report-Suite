"""infrastructure/time/fixed_clock.py — Deterministic IClock for testing."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from application.interfaces.i_clock import IClock


class FixedClock(IClock):
    """IClock implementation that always returns a caller-supplied timestamp.

    Useful in unit tests wherever a deterministic time is needed without
    monkeypatching.

    Usage::

        clock = FixedClock(datetime(2026, 1, 1, 12, 0, 0))
        assert clock.utcnow() == datetime(2026, 1, 1, 12, 0, 0)

        # Advance time programmatically in multi-step tests
        clock.advance(seconds=3600)
        assert clock.utcnow() == datetime(2026, 1, 1, 13, 0, 0)
    """

    def __init__(self, fixed: Optional[datetime] = None) -> None:
        """
        Args:
            fixed: The timestamp to return from ``utcnow()`` and
                ``now_local()``.  Defaults to 2024-01-01 00:00:00 UTC.
        """
        self._now: datetime = fixed or datetime(2024, 1, 1, 0, 0, 0)

    # ------------------------------------------------------------------ #
    # IClock                                                               #
    # ------------------------------------------------------------------ #

    def utcnow(self) -> datetime:
        return self._now

    def now_local(self) -> datetime:
        return self._now

    # ------------------------------------------------------------------ #
    # Test helpers                                                         #
    # ------------------------------------------------------------------ #

    def set(self, value: datetime) -> None:
        """Replace the fixed timestamp."""
        self._now = value

    def advance(
        self,
        *,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> None:
        """Move the clock forward by the given duration."""
        from datetime import timedelta
        self._now += timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
