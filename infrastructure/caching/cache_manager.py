"""
infrastructure/caching/cache_manager.py

Thread-safe in-process LRU cache with per-entry TTL.

Design
------
- ``InMemoryCache`` uses an ``OrderedDict`` as the LRU store: the most-recently
  accessed entry is moved to the end; when the capacity is exceeded the oldest
  (leftmost) entry is evicted.
- Each entry carries an absolute expiry timestamp (``time.monotonic() + ttl``).
  Expired entries are treated as misses and lazily removed on access.
- A background sweeper is NOT used — lazy eviction keeps the implementation
  simple and deterministic.  Call ``evict_expired()`` explicitly if you need
  to reclaim memory proactively.

Usage
-----
    from infrastructure.caching import get_cache

    cache = get_cache()
    cache.set("user:alice:profile", profile_dict, ttl=300)
    profile = cache.get("user:alice:profile")   # None on miss/expiry
    cache.delete("user:alice:profile")
    cache.clear()

    stats = cache.stats()
    # CacheStats(hits=4, misses=1, evictions=0, size=1, capacity=1024)
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Public protocol — allows alternative backends (Redis, Memcached…) later
# ---------------------------------------------------------------------------


@runtime_checkable
class ICacheBackend(Protocol):
    """Minimal cache backend contract."""

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value, or None if missing/expired."""
        ...

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store *value* under *key* with an optional TTL in seconds."""
        ...

    def delete(self, key: str) -> None:
        """Remove *key* (no-op if absent)."""
        ...

    def clear(self) -> None:
        """Remove all entries."""
        ...

    def exists(self, key: str) -> bool:
        """Return True if *key* exists and has not expired."""
        ...


# ---------------------------------------------------------------------------
# Cache statistics snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    evictions: int
    size: int
    capacity: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


# ---------------------------------------------------------------------------
# Internal entry
# ---------------------------------------------------------------------------


@dataclass
class _Entry:
    value: Any
    expires_at: float  # monotonic clock; math.inf means no expiry


# ---------------------------------------------------------------------------
# InMemoryCache
# ---------------------------------------------------------------------------


class InMemoryCache:
    """Thread-safe LRU cache with per-entry TTL.

    Parameters
    ----------
    capacity:
        Maximum number of entries to hold.  When full, the least-recently-used
        entry is evicted.  Default 1 024.
    default_ttl:
        TTL in seconds applied when ``set()`` is called without an explicit
        TTL.  ``None`` means entries never expire (until evicted by LRU).
    """

    def __init__(
        self,
        capacity: int = 1024,
        default_ttl: Optional[float] = 300.0,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None on miss/expiry."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.monotonic() >= entry.expires_at:
                # Lazy expiry
                del self._store[key]
                self._misses += 1
                self._evictions += 1
                return None
            # Move to end (most-recently used)
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store *value* under *key*.

        ``ttl`` overrides the instance ``default_ttl``; pass ``0`` for
        no expiry.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = (
            float("inf")
            if not effective_ttl
            else time.monotonic() + effective_ttl
        )
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            elif len(self._store) >= self._capacity:
                # Evict LRU (leftmost)
                self._store.popitem(last=False)
                self._evictions += 1
            self._store[key] = _Entry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def exists(self, key: str) -> bool:
        return self.get(key) is not None  # leverages hit/miss counting

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def evict_expired(self) -> int:
        """Proactively remove all expired entries.  Returns eviction count."""
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired_keys = [k for k, v in self._store.items() if now >= v.expires_at]
            for k in expired_keys:
                del self._store[k]
                removed += 1
            self._evictions += removed
        return removed

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                size=len(self._store),
                capacity=self._capacity,
            )

    def reset_stats(self) -> None:
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __repr__(self) -> str:
        s = self.stats()
        return (
            f"InMemoryCache(size={s.size}/{s.capacity}, "
            f"hits={s.hits}, misses={s.misses}, "
            f"hit_rate={s.hit_rate:.1%})"
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_cache: Optional[InMemoryCache] = None
_singleton_lock = threading.Lock()


def get_cache(capacity: int = 1024, default_ttl: Optional[float] = 300.0) -> InMemoryCache:
    """Return the process-wide singleton :class:`InMemoryCache`.

    Parameters are only applied on first creation; subsequent calls return the
    already-created instance regardless of arguments.
    """
    global _default_cache
    if _default_cache is None:
        with _singleton_lock:
            if _default_cache is None:
                _default_cache = InMemoryCache(capacity=capacity, default_ttl=default_ttl)
    return _default_cache
