"""tests/application/test_phase10_infrastructure_utils.py

Phase 10 — Infrastructure utility tests.

Covers:
- FixedClock: deterministic time, advance helpers
- LruCacheService: ICacheService contract over InMemoryCache
- SequentialIdGenerator: thread-safe integer sequences
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import List

import pytest

from application.interfaces.i_cache_service import ICacheService
from application.interfaces.i_clock import IClock
from application.interfaces.i_id_generator import IIdGenerator
from infrastructure.caching.lru_cache_service import LruCacheService
from infrastructure.identity.sequential_id_generator import SequentialIdGenerator
from infrastructure.time.fixed_clock import FixedClock


# ---------------------------------------------------------------------------
# FixedClock
# ---------------------------------------------------------------------------

class TestFixedClock:
    """FixedClock satisfies IClock and provides test helpers."""

    def test_is_subclass_of_interface(self) -> None:
        assert issubclass(FixedClock, IClock)

    def test_default_timestamp(self) -> None:
        clock = FixedClock()
        assert clock.utcnow() == datetime(2024, 1, 1, 0, 0, 0)

    def test_custom_timestamp(self) -> None:
        ts = datetime(2026, 6, 15, 8, 30, 0)
        clock = FixedClock(ts)
        assert clock.utcnow() == ts

    def test_now_local_returns_same_as_utcnow(self) -> None:
        ts = datetime(2026, 3, 20, 12, 0, 0)
        clock = FixedClock(ts)
        assert clock.now_local() == ts

    def test_utcnow_is_stable(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1))
        first = clock.utcnow()
        second = clock.utcnow()
        assert first == second

    def test_set_changes_timestamp(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1))
        new_ts = datetime(2026, 12, 31, 23, 59, 59)
        clock.set(new_ts)
        assert clock.utcnow() == new_ts

    def test_advance_hours(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1, 10, 0, 0))
        clock.advance(hours=3)
        assert clock.utcnow() == datetime(2026, 1, 1, 13, 0, 0)

    def test_advance_days(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1))
        clock.advance(days=7)
        assert clock.utcnow() == datetime(2026, 1, 8)

    def test_advance_combined(self) -> None:
        clock = FixedClock(datetime(2026, 4, 1, 0, 0, 0))
        clock.advance(days=1, hours=2, minutes=30, seconds=15)
        assert clock.utcnow() == datetime(2026, 4, 2, 2, 30, 15)

    def test_advance_multiple_times(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1))
        clock.advance(hours=1)
        clock.advance(hours=1)
        assert clock.utcnow() == datetime(2026, 1, 1, 2, 0, 0)

    def test_usable_in_service_instead_of_default_clock(self) -> None:
        """Confirms FixedClock works as a drop-in for DefaultClock."""
        from application.interfaces.i_clock import IClock
        clock: IClock = FixedClock(datetime(2026, 5, 1))
        assert clock.utcnow().year == 2026


# ---------------------------------------------------------------------------
# SequentialIdGenerator
# ---------------------------------------------------------------------------

class TestSequentialIdGenerator:
    """SequentialIdGenerator satisfies IIdGenerator and is thread-safe."""

    def test_is_subclass_of_interface(self) -> None:
        assert issubclass(SequentialIdGenerator, IIdGenerator)

    def test_returns_string(self) -> None:
        gen = SequentialIdGenerator()
        assert isinstance(gen.new_id(), str)

    def test_starts_at_1_by_default(self) -> None:
        gen = SequentialIdGenerator()
        assert gen.new_id() == "1"

    def test_increments_by_1(self) -> None:
        gen = SequentialIdGenerator()
        ids = [gen.new_id() for _ in range(5)]
        assert ids == ["1", "2", "3", "4", "5"]

    def test_custom_start(self) -> None:
        gen = SequentialIdGenerator(start=100)
        assert gen.new_id() == "100"
        assert gen.new_id() == "101"

    def test_custom_step(self) -> None:
        gen = SequentialIdGenerator(start=10, step=10)
        ids = [gen.new_id() for _ in range(3)]
        assert ids == ["10", "20", "30"]

    def test_step_less_than_1_raises(self) -> None:
        with pytest.raises(ValueError):
            SequentialIdGenerator(step=0)

    def test_int_cast_works(self) -> None:
        gen = SequentialIdGenerator(start=42)
        assert int(gen.new_id()) == 42

    def test_current_property_peeks_without_advancing(self) -> None:
        gen = SequentialIdGenerator(start=5)
        assert gen.current == 5
        gen.new_id()
        assert gen.current == 6

    def test_thread_safe_unique_ids(self) -> None:
        """All IDs produced across multiple threads must be unique."""
        gen = SequentialIdGenerator(start=1)
        collected: List[str] = []
        lock = threading.Lock()

        def worker() -> None:
            for _ in range(50):
                id_ = gen.new_id()
                with lock:
                    collected.append(id_)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(collected) == 500
        assert len(set(collected)) == 500, "Duplicate IDs detected under concurrency"


# ---------------------------------------------------------------------------
# LruCacheService
# ---------------------------------------------------------------------------

class TestLruCacheService:
    """LruCacheService satisfies ICacheService over the LRU InMemoryCache."""

    def test_is_subclass_of_interface(self) -> None:
        assert issubclass(LruCacheService, ICacheService)

    def test_set_and_get(self) -> None:
        cache = LruCacheService()
        cache.set("k1", "value1")
        assert cache.get("k1") == "value1"

    def test_get_missing_key_returns_none(self) -> None:
        cache = LruCacheService()
        assert cache.get("nonexistent") is None

    def test_delete(self) -> None:
        cache = LruCacheService()
        cache.set("k2", 42)
        cache.delete("k2")
        assert cache.get("k2") is None

    def test_delete_nonexistent_is_noop(self) -> None:
        cache = LruCacheService()
        cache.delete("no-such-key")  # should not raise

    def test_clear_all(self) -> None:
        cache = LruCacheService()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_clear_namespace(self) -> None:
        cache = LruCacheService()
        cache.set("case:C-001", "data1")
        cache.set("case:C-002", "data2")
        cache.set("report:R-001", "rdata")
        cache.clear("case")
        assert cache.get("case:C-001") is None
        assert cache.get("case:C-002") is None
        assert cache.get("report:R-001") == "rdata"  # different namespace untouched

    def test_clear_namespace_with_no_matches_is_safe(self) -> None:
        cache = LruCacheService()
        cache.set("x:1", "v")
        cache.clear("other")
        assert cache.get("x:1") == "v"

    def test_ttl_expiry(self) -> None:
        """Entry expires after TTL elapses (use very small TTL and sleep)."""
        import time
        cache = LruCacheService(default_ttl=0.05)
        cache.set("expiring", "soon")  # uses default_ttl=0.05s
        time.sleep(0.1)
        assert cache.get("expiring") is None

    def test_explicit_ttl_overrides_default(self) -> None:
        cache = LruCacheService(default_ttl=0.01)
        # Explicit large TTL — entry should still be present after a tiny sleep
        import time
        cache.set("long-lived", "val", ttl_seconds=3600)
        time.sleep(0.05)
        assert cache.get("long-lived") == "val"

    def test_lru_eviction(self) -> None:
        """When capacity is exceeded, LRU entry is evicted."""
        cache = LruCacheService(capacity=2, default_ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # touch 'a' → 'b' is now LRU
        cache.set("c", 3)  # evicts 'b'
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3

    def test_stores_various_value_types(self) -> None:
        cache = LruCacheService()
        cache.set("int", 99)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"k": "v"})
        cache.set("none", None)
        assert cache.get("int") == 99
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"k": "v"}
        assert cache.get("none") is None  # None stored and None on miss — same result


# ---------------------------------------------------------------------------
# infrastructure/time __init__ exports
# ---------------------------------------------------------------------------

class TestTimePackageExports:
    def test_fixed_clock_exported(self) -> None:
        from infrastructure.time import FixedClock  # noqa: F401

    def test_system_clock_still_exported(self) -> None:
        from infrastructure.time import SystemClock  # noqa: F401

    def test_fixed_clock_in_all(self) -> None:
        import infrastructure.time as pkg
        assert "FixedClock" in pkg.__all__


# ---------------------------------------------------------------------------
# infrastructure/identity __init__ exports
# ---------------------------------------------------------------------------

class TestIdentityPackageExports:
    def test_sequential_id_generator_exported(self) -> None:
        from infrastructure.identity import SequentialIdGenerator  # noqa: F401

    def test_uuid_id_generator_still_exported(self) -> None:
        from infrastructure.identity import UuidIdGenerator  # noqa: F401

    def test_sequential_in_all(self) -> None:
        import infrastructure.identity as pkg
        assert "SequentialIdGenerator" in pkg.__all__


# ---------------------------------------------------------------------------
# infrastructure/caching __init__ exports
# ---------------------------------------------------------------------------

class TestCachingPackageExports:
    def test_lru_cache_service_exported(self) -> None:
        from infrastructure.caching import LruCacheService  # noqa: F401

    def test_lru_cache_service_in_all(self) -> None:
        import infrastructure.caching as pkg
        assert "LruCacheService" in pkg.__all__
