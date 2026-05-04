"""
infrastructure/caching/ — In-process cache abstraction with TTL and LRU eviction.

Provides:
- ICacheBackend: protocol for pluggable backends
- InMemoryCache: thread-safe LRU+TTL in-process cache
- @cached decorator for Flask/service functions
- get_cache(): process-wide singleton
"""

from infrastructure.caching.cache_manager import (
    ICacheBackend,
    InMemoryCache,
    get_cache,
    CacheStats,
)
from infrastructure.caching.decorators import cached, cache_invalidate
from infrastructure.caching.lru_cache_service import LruCacheService

__all__ = [
    "ICacheBackend",
    "InMemoryCache",
    "get_cache",
    "CacheStats",
    "cached",
    "cache_invalidate",
    "LruCacheService",
]
