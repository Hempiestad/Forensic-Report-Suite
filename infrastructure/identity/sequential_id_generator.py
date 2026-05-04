"""infrastructure/identity/sequential_id_generator.py — Integer sequence ID generator."""
from __future__ import annotations

import threading

from application.interfaces.i_id_generator import IIdGenerator


class SequentialIdGenerator(IIdGenerator):
    """Thread-safe monotonically-increasing integer ID generator.

    Primarily used for entity types that rely on integer primary keys (e.g.
    ``Evidence.id``).  The returned value is a *string* to satisfy the
    ``IIdGenerator`` contract; callers that need an ``int`` can cast with
    ``int(gen.new_id())``.

    Usage::

        gen = SequentialIdGenerator(start=1)
        assert gen.new_id() == "1"
        assert gen.new_id() == "2"

        # With a custom step
        gen2 = SequentialIdGenerator(start=100, step=10)
        assert gen2.new_id() == "100"
        assert gen2.new_id() == "110"
    """

    def __init__(self, start: int = 1, step: int = 1) -> None:
        """
        Args:
            start: First value returned by ``new_id()``.
            step: Increment applied on each call.
        """
        if step < 1:
            raise ValueError("step must be >= 1")
        self._current = start
        self._step = step
        self._lock = threading.Lock()

    def new_id(self) -> str:
        with self._lock:
            value = self._current
            self._current += self._step
        return str(value)

    @property
    def current(self) -> int:
        """Peek at the next value that will be issued (without advancing)."""
        with self._lock:
            return self._current
