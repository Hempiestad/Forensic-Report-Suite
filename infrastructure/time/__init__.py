"""infrastructure/time - Time provider implementations."""

from infrastructure.time.system_clock import SystemClock
from infrastructure.time.fixed_clock import FixedClock

__all__ = ["SystemClock", "FixedClock"]
