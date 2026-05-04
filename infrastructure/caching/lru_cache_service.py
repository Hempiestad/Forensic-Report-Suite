"""infrastructure/caching/lru_cache_service.py — LRU-backed ICacheService."""
from __future__ import annotations

from typing import Any, Optional

from application.interfaces.i_cache_service import ICacheService
from infrastructure.caching.cache_manager import InMemoryCache


class LruCacheService(ICacheService):
    """ICacheService adapter backed by the thread-safe LRU InMemoryCache.

    This bridges the infrastructure-level ``InMemoryCache`` (which exposes
    the lower-level ``ICacheBackend`` protocol) to the application-layer
    ``ICacheService`` contract used by application services.

    Namespace convention: ``"namespace:key"`` — ``clear(namespace)`` removes
    all entries whose key starts with ``"namespace:"``.

    Usage::

        from infrastructure.caching.lru_cache_service import LruCacheService

        cache = LruCacheService(capacity=2048, default_ttl=300)
        cache.set("case:C-001", case_data, ttl_seconds=60)
        data = cache.get("case:C-001")   # returns case_data
        cache.delete("case:C-001")
        cache.clear("case")              # removes all "case:*" keys
    """

    def __init__(
        self,
        capacity: int = 1024,
        default_ttl: Optional[float] = 300.0,
        _cache: Optional[InMemoryCache] = None,
    ) -> None:
        """
        Args:
            capacity: Maximum entries before LRU eviction.
            default_ttl: Seconds before an entry expires (``None`` = no expiry).
            _cache: Pre-built ``InMemoryCache`` instance (for testing).
        """
        self._cache = _cache or InMemoryCache(capacity=capacity, default_ttl=default_ttl)

    # ------------------------------------------------------------------ #
    # ICacheService                                                        #
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        self._cache.set(key, value, ttl=float(ttl_seconds) if ttl_seconds is not None else None)

    def delete(self, key: str) -> None:
        self._cache.delete(key)

    def clear(self, namespace: Optional[str] = None) -> None:
        if namespace is None:
            self._cache.clear()
        else:
            prefix = f"{namespace}:"
            # Collect keys matching the namespace prefix then delete them.
            # InMemoryCache doesn't expose a key-listing API publicly, so we
            # access the internal store under lock via evict_expired first to
            # keep the store clean, then iterate.
            self._cache.evict_expired()
            with self._cache._lock:
                matching = [k for k in self._cache._store if k.startswith(prefix)]
                for k in matching:
                    del self._cache._store[k]
