"""
infrastructure/caching/decorators.py

Function-level cache decorators.

Usage
-----
    from infrastructure.caching import cached, cache_invalidate

    @cached(ttl=60, key_prefix="case")
    def get_case(case_number: str) -> dict:
        ...  # expensive DB call

    # Invalidate by key
    cache_invalidate("case", "get_case", "C-001")

    # Or invalidate by prefix pattern
    cache_invalidate("case")  # clears all keys starting with "case:"
"""

from __future__ import annotations

import functools
import hashlib
import json
from typing import Any, Callable, Optional, TypeVar

from infrastructure.caching.cache_manager import ICacheBackend, InMemoryCache, get_cache
from infrastructure.observability.metrics_collector import get_metrics

F = TypeVar("F", bound=Callable[..., Any])


def _make_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """Build a deterministic cache key from function identity and arguments."""
    try:
        args_repr = json.dumps((list(args), kwargs), sort_keys=True, default=str)
    except (TypeError, ValueError):
        # Fallback: hash the repr
        args_repr = hashlib.md5(repr((args, kwargs)).encode()).hexdigest()  # noqa: S324
    return f"{prefix}:{func_name}:{args_repr}"


def cached(
    ttl: Optional[float] = 300.0,
    key_prefix: str = "",
    cache: Optional[InMemoryCache] = None,
    skip_cache_on: Optional[type] = None,
) -> Callable[[F], F]:
    """Cache the return value of a function in the in-process LRU cache.

    Parameters
    ----------
    ttl:
        Time-to-live in seconds (``None`` = no expiry).
    key_prefix:
        String prepended to the generated cache key.
    cache:
        Override the cache instance (default: singleton from ``get_cache()``).
    skip_cache_on:
        If the wrapped function raises this exception type, the error is
        propagated without caching.  (Default: cache misses on any exception.)
    """

    def decorator(func: F) -> F:
        prefix = key_prefix or func.__module__ or "cache"
        metrics = get_metrics()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _cache = cache or get_cache()
            key = _make_cache_key(prefix, func.__qualname__, args, kwargs)

            cached_value = _cache.get(key)
            if cached_value is not None:
                metrics.increment(
                    "cache.hits",
                    tags={"function": func.__qualname__},
                )
                return cached_value

            metrics.increment(
                "cache.misses",
                tags={"function": func.__qualname__},
            )
            result = func(*args, **kwargs)
            if result is not None:
                _cache.set(key, result, ttl=ttl)
            return result

        # Attach cache key builder so callers can compute keys for invalidation
        wrapper._cache_key_prefix = prefix  # type: ignore[attr-defined]
        wrapper._cache_func_name = func.__qualname__  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def cache_invalidate(
    key_prefix: str,
    func_name: str = "",
    *args: Any,
    cache: Optional[InMemoryCache] = None,
    **kwargs: Any,
) -> None:
    """Remove a specific cached entry or all entries matching a prefix.

    Parameters
    ----------
    key_prefix:
        The prefix passed to ``@cached``.
    func_name:
        The qualified name of the cached function.  If omitted, all keys
        starting with ``key_prefix:`` are removed (prefix invalidation).
    *args / **kwargs:
        Arguments used when the cached function was called.
    cache:
        Override the cache instance.
    """
    _cache = cache or get_cache()

    if not func_name:
        # Prefix invalidation — scan and delete all matching keys
        # InMemoryCache doesn't expose keys directly; rebuild from the internal store.
        if hasattr(_cache, "_store"):
            import threading as _threading  # avoid name collision
            with _cache._lock:  # type: ignore[attr-defined]
                target_prefix = f"{key_prefix}:"
                keys_to_delete = [k for k in _cache._store if k.startswith(target_prefix)]  # type: ignore[attr-defined]
            for k in keys_to_delete:
                _cache.delete(k)
        return

    key = _make_cache_key(key_prefix, func_name, args, kwargs)
    _cache.delete(key)
