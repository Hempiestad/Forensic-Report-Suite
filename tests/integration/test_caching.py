"""
tests/integration/test_caching.py

Tests for infrastructure.caching — InMemoryCache, @cached decorator,
cache_invalidate, CacheStats, and the ICacheBackend protocol.
"""

from __future__ import annotations

import threading
import time

import pytest

from infrastructure.caching import (
    InMemoryCache,
    CacheStats,
    ICacheBackend,
    cached,
    cache_invalidate,
    get_cache,
)


# ===========================================================================
# InMemoryCache — basic get/set
# ===========================================================================


class TestInMemoryCacheBasic:
    def setup_method(self):
        self.cache = InMemoryCache(capacity=10, default_ttl=60.0)

    def test_set_and_get(self):
        self.cache.set("k1", "value1")
        assert self.cache.get("k1") == "value1"

    def test_miss_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_overwrite_value(self):
        self.cache.set("k", "first")
        self.cache.set("k", "second")
        assert self.cache.get("k") == "second"

    def test_delete_removes_entry(self):
        self.cache.set("k", "v")
        self.cache.delete("k")
        assert self.cache.get("k") is None

    def test_delete_nonexistent_is_noop(self):
        self.cache.delete("ghost")  # must not raise

    def test_clear_removes_all_entries(self):
        for i in range(5):
            self.cache.set(f"k{i}", i)
        self.cache.clear()
        for i in range(5):
            assert self.cache.get(f"k{i}") is None

    def test_exists_true_for_present_key(self):
        self.cache.set("k", 42)
        assert self.cache.exists("k") is True

    def test_exists_false_for_absent_key(self):
        assert self.cache.exists("missing") is False

    def test_len(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        assert len(self.cache) == 2

    def test_stores_various_types(self):
        self.cache.set("list", [1, 2, 3])
        self.cache.set("dict", {"x": 1})
        self.cache.set("none", None)  # None is allowed for set but treated as miss on get
        assert self.cache.get("list") == [1, 2, 3]
        assert self.cache.get("dict") == {"x": 1}


# ===========================================================================
# TTL expiry
# ===========================================================================


class TestTTL:
    def test_entry_expires_after_ttl(self):
        cache = InMemoryCache(default_ttl=0.05)  # 50 ms
        cache.set("k", "v")
        time.sleep(0.07)
        assert cache.get("k") is None

    def test_entry_alive_before_ttl(self):
        cache = InMemoryCache(default_ttl=5.0)
        cache.set("k", "v")
        assert cache.get("k") == "v"

    def test_per_entry_ttl_overrides_default(self):
        cache = InMemoryCache(default_ttl=60.0)
        cache.set("k", "v", ttl=0.05)  # short per-entry TTL
        time.sleep(0.07)
        assert cache.get("k") is None

    def test_ttl_zero_means_no_expiry(self):
        cache = InMemoryCache(default_ttl=0)
        cache.set("k", "forever")
        assert cache.get("k") == "forever"

    def test_evict_expired_removes_stale_entries(self):
        cache = InMemoryCache(default_ttl=0.05)
        for i in range(5):
            cache.set(f"k{i}", i)
        time.sleep(0.07)
        removed = cache.evict_expired()
        assert removed == 5
        assert len(cache) == 0


# ===========================================================================
# LRU eviction
# ===========================================================================


class TestLRUEviction:
    def test_capacity_respected(self):
        cache = InMemoryCache(capacity=3, default_ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert len(cache) == 3
        cache.set("d", 4)  # 'a' should be evicted (LRU)
        assert len(cache) == 3
        assert cache.get("a") is None  # evicted
        assert cache.get("d") == 4

    def test_access_refreshes_lru_order(self):
        cache = InMemoryCache(capacity=3, default_ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")   # refresh 'a' → now 'b' is LRU
        cache.set("d", 4)
        assert cache.get("b") is None  # 'b' was evicted
        assert cache.get("a") == 1

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            InMemoryCache(capacity=0)


# ===========================================================================
# CacheStats
# ===========================================================================


class TestCacheStats:
    def test_stats_initial(self):
        cache = InMemoryCache()
        s = cache.stats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.evictions == 0
        assert s.size == 0

    def test_stats_after_hits_and_misses(self):
        cache = InMemoryCache()
        cache.set("k", "v")
        cache.get("k")   # hit
        cache.get("k")   # hit
        cache.get("x")   # miss
        s = cache.stats()
        assert s.hits == 2
        assert s.misses == 1
        assert s.hit_rate == pytest.approx(2 / 3)

    def test_stats_eviction_on_capacity(self):
        cache = InMemoryCache(capacity=2, default_ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # evicts 'a'
        assert cache.stats().evictions == 1

    def test_reset_stats(self):
        cache = InMemoryCache()
        cache.set("k", "v")
        cache.get("k")
        cache.get("x")
        cache.reset_stats()
        s = cache.stats()
        assert s.hits == 0
        assert s.misses == 0

    def test_frozen_stats_dataclass(self):
        s = CacheStats(hits=1, misses=0, evictions=0, size=1, capacity=100)
        with pytest.raises(Exception):
            s.hits = 2  # frozen dataclass


# ===========================================================================
# ICacheBackend protocol compliance
# ===========================================================================


class TestProtocol:
    def test_inmemory_implements_protocol(self):
        cache = InMemoryCache()
        assert isinstance(cache, ICacheBackend)


# ===========================================================================
# @cached decorator
# ===========================================================================


class TestCachedDecorator:
    def setup_method(self):
        self._cache = InMemoryCache(default_ttl=60.0)
        self.call_count = 0

    def test_result_is_cached(self):
        @cached(ttl=60, key_prefix="test", cache=self._cache)
        def expensive(x: int) -> int:
            self.call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10  # second call should hit cache
        assert self.call_count == 1

    def test_different_args_cached_separately(self):
        @cached(ttl=60, key_prefix="test", cache=self._cache)
        def square(n: int) -> int:
            self.call_count += 1
            return n * n

        assert square(3) == 9
        assert square(4) == 16
        assert self.call_count == 2  # both computed

    def test_cache_expires(self):
        @cached(ttl=0.05, key_prefix="test_exp", cache=self._cache)
        def val(x: int) -> int:
            self.call_count += 1
            return x

        val(1)
        time.sleep(0.07)
        val(1)
        assert self.call_count == 2  # recomputed after expiry

    def test_none_result_not_cached(self):
        @cached(ttl=60, key_prefix="test_none", cache=self._cache)
        def maybe_none(flag: bool):
            self.call_count += 1
            return None if not flag else "value"

        maybe_none(False)
        maybe_none(False)
        assert self.call_count == 2  # None not cached → called again


# ===========================================================================
# cache_invalidate
# ===========================================================================


class TestCacheInvalidate:
    def setup_method(self):
        self._cache = InMemoryCache(default_ttl=60.0)
        self.call_count = 0

    def _make_fn(self):
        @cached(ttl=60, key_prefix="inv_test", cache=self._cache)
        def fn(x: int) -> int:
            self.call_count += 1
            return x
        return fn

    def test_invalidate_specific_key(self):
        fn = self._make_fn()
        fn(7)
        assert self.call_count == 1
        cache_invalidate("inv_test", fn._cache_func_name, 7, cache=self._cache)
        fn(7)
        assert self.call_count == 2  # recomputed

    def test_invalidate_prefix_clears_all_matching(self):
        fn = self._make_fn()
        fn(1)
        fn(2)
        fn(3)
        assert self.call_count == 3
        cache_invalidate("inv_test", cache=self._cache)
        fn(1)
        fn(2)
        assert self.call_count == 5  # recomputed


# ===========================================================================
# Thread safety
# ===========================================================================


class TestThreadSafety:
    def test_concurrent_writes(self):
        cache = InMemoryCache(capacity=1000, default_ttl=None)
        threads = [
            threading.Thread(target=lambda i=i: cache.set(f"k{i}", i))
            for i in range(100)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(cache) == 100

    def test_concurrent_reads_and_writes(self):
        cache = InMemoryCache(default_ttl=None)
        cache.set("shared", 0)
        results = []

        def reader():
            for _ in range(20):
                v = cache.get("shared")
                if v is not None:
                    results.append(v)

        def writer():
            for i in range(20):
                cache.set("shared", i)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # No assertion on values — just must not crash/deadlock


# ===========================================================================
# get_cache() singleton
# ===========================================================================


class TestGetCacheSingleton:
    def test_returns_same_instance(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2
