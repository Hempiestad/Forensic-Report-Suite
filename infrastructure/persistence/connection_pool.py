"""infrastructure/persistence/connection_pool.py

Provides a singleton PostgreSQL connection pool per DSN using psycopg_pool.
Each DSN gets exactly one shared pool; UnitOfWork borrows connections from it.

Usage:
    pool = get_or_create_pool(dsn, min_size=2, max_size=10)
    with pool.connection() as conn:
        ...  # automatic release back to pool

Pool lifecycle:
    - Created lazily on first call to get_or_create_pool
    - Shared across all UnitOfWork instances for the same DSN
    - Closed explicitly via close_pool(dsn) or close_all_pools()
    - Thread-safe via threading.Lock
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Thread-safe registry: DSN -> pool instance
_registry: Dict[str, Any] = {}
_registry_lock = threading.Lock()

# Type alias to avoid circular import issues at module level
try:
    from psycopg_pool import ConnectionPool as _ConnectionPool  # noqa: F401
    _pool_available = True
except ImportError:
    _pool_available = False


@dataclass
class PoolConfig:
    """Configuration for a PostgreSQL connection pool.

    Args:
        min_size: Minimum number of idle connections maintained in the pool.
        max_size: Maximum number of connections the pool will open.
        max_waiting: Max number of requests that can wait when pool is full.
        timeout: Seconds to wait for a connection before raising PoolTimeout.
        max_idle: Seconds a connection can sit idle before being recycled.
        reconnect_timeout: Seconds to attempt reconnect after server disconnect.
        open: Whether to open the pool immediately on creation.
    """
    min_size: int = 2
    max_size: int = 10
    max_waiting: int = 50
    timeout: float = 30.0
    max_idle: float = 300.0
    reconnect_timeout: float = 60.0
    open: bool = True


def _make_pool(dsn: str, config: PoolConfig) -> Any:
    """Create a new psycopg_pool.ConnectionPool for the given DSN."""
    if not _pool_available:
        raise RuntimeError(
            "Connection pooling requires psycopg-pool. "
            "Install with: pip install 'psycopg-pool>=3.2'"
        )

    try:
        from psycopg_pool import ConnectionPool
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "psycopg or psycopg-pool is not installed. "
            "Install with: pip install 'psycopg[binary]' 'psycopg-pool>=3.2'"
        ) from exc

    logger.info(
        "Creating PostgreSQL connection pool: min=%d max=%d dsn=%s",
        config.min_size,
        config.max_size,
        _redact_dsn(dsn),
    )

    pool = ConnectionPool(
        conninfo=dsn,
        min_size=config.min_size,
        max_size=config.max_size,
        max_waiting=config.max_waiting,
        timeout=config.timeout,
        max_idle=config.max_idle,
        reconnect_timeout=config.reconnect_timeout,
        open=config.open,
        kwargs={"row_factory": dict_row, "autocommit": False},
        name=f"forensic-pool-{_redact_dsn(dsn)}",
    )

    logger.info("PostgreSQL connection pool created successfully.")
    return pool


def get_or_create_pool(
    dsn: str,
    config: Optional[PoolConfig] = None,
) -> Any:
    """Return the shared pool for *dsn*, creating it if not yet present.

    This is the primary entry-point for consumers (UnitOfWork, tests).
    Thread-safe: only one pool is created per unique DSN.

    Args:
        dsn: PostgreSQL connection string.
        config: Pool configuration.  Defaults to PoolConfig() if not supplied.
                If the pool already exists the config is ignored — the pool is
                not recreated; call close_pool(dsn) first if you need new settings.

    Returns:
        A psycopg_pool.ConnectionPool instance.
    """
    with _registry_lock:
        if dsn not in _registry:
            _registry[dsn] = _make_pool(dsn, config or PoolConfig())
        return _registry[dsn]


def close_pool(dsn: str) -> None:
    """Close and remove the pool for *dsn* from the registry.

    Waits for all active connections to be returned before closing.
    Safe to call even if no pool exists for the given DSN.
    """
    with _registry_lock:
        pool = _registry.pop(dsn, None)
    if pool is not None:
        logger.info("Closing PostgreSQL connection pool for %s.", _redact_dsn(dsn))
        pool.close()
        logger.info("Pool closed.")


def close_all_pools() -> None:
    """Close every registered pool.  Useful for graceful shutdown."""
    with _registry_lock:
        dsns = list(_registry.keys())
        pools = [_registry.pop(d) for d in dsns]

    for pool in pools:
        try:
            pool.close()
        except Exception:  # pragma: no cover
            logger.exception("Error closing pool during shutdown.")
    if dsns:
        logger.info("Closed %d PostgreSQL connection pool(s).", len(dsns))


def pool_stats(dsn: str) -> Dict[str, Any]:
    """Return current statistics for the pool registered against *dsn*.

    Returns an empty dict if no pool exists for that DSN.
    """
    pool = _registry.get(dsn)
    if pool is None:
        return {}
    stats = pool.get_stats()
    stats["dsn_redacted"] = _redact_dsn(dsn)
    return stats


def _redact_dsn(dsn: str) -> str:
    """Replace the password portion of a DSN with ***."""
    import re
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", dsn)


# ---------------------------------------------------------------------------
# Type placeholder so that the module can be imported without psycopg_pool
# ---------------------------------------------------------------------------
try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from psycopg_pool import ConnectionPool as Any  # type: ignore[assignment]
except ImportError:
    pass

from typing import Any  # noqa: E402 – make sure Any is always defined
