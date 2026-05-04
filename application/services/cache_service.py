"""application/services/cache_service.py — InMemoryCacheService (Phase 6)."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from application.interfaces.i_cache_service import ICacheService

# Internal slot: (value, expiry_timestamp | None)
_Slot = Tuple[Any, Optional[float]]


class InMemoryCacheService(ICacheService):
    """Thread-naive TTL-aware in-memory cache.

    Namespace convention: use ``"namespace:key"`` to group related entries.
    """

    def __init__(self) -> None:
        self._store: Dict[str, _Slot] = {}

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _is_expired(self, slot: _Slot) -> bool:
        _, expiry = slot
        return expiry is not None and time.monotonic() > expiry

    def _evict_expired(self) -> None:
        expired_keys = [k for k, v in self._store.items() if self._is_expired(v)]
        for k in expired_keys:
            del self._store[k]

    # ------------------------------------------------------------------ #
    # ICacheService                                                        #
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Optional[Any]:
        slot = self._store.get(key)
        if slot is None:
            return None
        if self._is_expired(slot):
            del self._store[key]
            return None
        return slot[0]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        expiry: Optional[float] = (
            time.monotonic() + ttl_seconds if ttl_seconds is not None else None
        )
        self._store[key] = (value, expiry)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self, namespace: Optional[str] = None) -> None:
        if namespace is None:
            self._store.clear()
        else:
            prefix = namespace if namespace.endswith(":") else namespace + ":"
            keys_to_delete = [k for k in self._store if k == namespace or k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]
