from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemorySlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check_and_consume(self, bucket_key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.time()
        window_start = now - float(window_seconds)

        with self._lock:
            q = self._events[bucket_key]
            while q and q[0] <= window_start:
                q.popleft()

            used = len(q)
            if used >= limit:
                retry_after = max(1, int(q[0] + window_seconds - now)) if q else window_seconds
                return RateLimitDecision(allowed=False, remaining=0, retry_after_seconds=retry_after)

            q.append(now)
            remaining = max(0, limit - len(q))
            return RateLimitDecision(allowed=True, remaining=remaining, retry_after_seconds=0)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
