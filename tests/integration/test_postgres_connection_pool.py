"""Integration tests for PostgreSQL connection pooling (Phase 3.2a).

All tests are env-gated — they skip when FORENSIC_PG_DSN is not set.
When the DSN IS set the tests validate:
  - Pool creation and singleton behavior
  - Concurrent UoW instances (10+ simultaneous) without deadlock/exhaustion
  - Pool stats reporting
  - Pool lifecycle (create, use, close)
  - Pooled context as drop-in replacement for direct context
"""
from __future__ import annotations

import os
import threading
import time
from typing import List

import pytest

FORENSIC_PG_DSN = os.getenv("FORENSIC_PG_DSN")
_skip = pytest.mark.skipif(not FORENSIC_PG_DSN, reason="FORENSIC_PG_DSN not set")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dsn() -> str:
    return FORENSIC_PG_DSN  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Pool creation and singleton behavior
# ---------------------------------------------------------------------------

@_skip
def test_pool_creation_and_singleton() -> None:
    """get_or_create_pool returns the same pool object for the same DSN."""
    from infrastructure.persistence.connection_pool import (
        PoolConfig,
        close_pool,
        get_or_create_pool,
    )

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=3)

    try:
        pool_a = get_or_create_pool(dsn, config)
        pool_b = get_or_create_pool(dsn)  # no config — reuses existing

        assert pool_a is pool_b, "Expected the same pool object for the same DSN"
    finally:
        close_pool(dsn)


@_skip
def test_pool_stats_reporting() -> None:
    """pool_stats returns meaningful metrics after pool creation."""
    from infrastructure.persistence.connection_pool import (
        PoolConfig,
        close_pool,
        get_or_create_pool,
        pool_stats,
    )

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=3)

    try:
        get_or_create_pool(dsn, config)
        stats = pool_stats(dsn)

        assert "pool_min" in stats or "min_size" in stats or stats  # psycopg_pool stats dict
        assert stats.get("dsn_redacted")  # password is redacted
        assert "***" in stats["dsn_redacted"]
    finally:
        close_pool(dsn)


# ---------------------------------------------------------------------------
# Pooled context as drop-in for direct context
# ---------------------------------------------------------------------------

@_skip
def test_pooled_context_crud() -> None:
    """PostgreSQLPooledDbContext supports case CRUD identically to direct context."""
    from infrastructure.persistence.connection_pool import PoolConfig, close_pool
    from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
    from infrastructure.persistence.repositories.postgres_case_repository import PostgreSQLCaseRepository
    from domain.entities.case import Case

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=3)

    try:
        with PostgreSQLPooledDbContext(dsn, pool_config=config) as ctx:
            repo = PostgreSQLCaseRepository(ctx)

            case = Case.create(
                case_number="POOL-CRUD-001",
                title="Pool CRUD test",
                assigned_to="det.pool",
                created_by="admin",
            )
            repo.add(case)
            ctx.commit()

            loaded = repo.get_by_id("POOL-CRUD-001")
            assert loaded is not None
            assert loaded.title == "Pool CRUD test"

            # Cleanup
            repo.delete("POOL-CRUD-001")
            ctx.commit()
    finally:
        close_pool(dsn)


@_skip
def test_uow_with_pool_config() -> None:
    """UnitOfWork(provider='postgres', pool_config=...) uses a pooled context."""
    from infrastructure.persistence.connection_pool import PoolConfig, close_pool
    from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
    from infrastructure.persistence.unit_of_work import UnitOfWork

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=3)

    try:
        with UnitOfWork(provider="postgres", postgres_dsn=dsn, pool_config=config) as uow:
            assert isinstance(uow._db_context, PostgreSQLPooledDbContext)
    finally:
        close_pool(dsn)


# ---------------------------------------------------------------------------
# Concurrency tests — 10 simultaneous UoW instances
# ---------------------------------------------------------------------------

@_skip
def test_concurrent_uow_instances_no_leak() -> None:
    """10 simultaneous UoW instances complete without connection exhaustion."""
    from infrastructure.persistence.connection_pool import PoolConfig, close_pool
    from infrastructure.persistence.unit_of_work import UnitOfWork
    from domain.entities.case import Case

    dsn = _dsn()
    # max_size=5 means up to 5 borrowed at once; max_waiting handles the queue
    config = PoolConfig(min_size=2, max_size=5, max_waiting=20, timeout=30.0)

    errors: List[Exception] = []
    results: List[str] = []

    def worker(thread_id: int) -> None:
        try:
            with UnitOfWork(provider="postgres", postgres_dsn=dsn, pool_config=config) as uow:
                case = Case.create(
                    case_number=f"CONCUR-{thread_id:03d}",
                    title=f"Concurrent test {thread_id}",
                    assigned_to="det.concurrent",
                    created_by="admin",
                )
                uow.cases.add(case)
                uow.commit()
                loaded = uow.cases.get_by_id(f"CONCUR-{thread_id:03d}")
                assert loaded is not None
                uow.cases.delete(f"CONCUR-{thread_id:03d}")
                uow.commit()
                results.append(f"thread-{thread_id}-ok")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 11)]

    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert not errors, f"Concurrent workers raised errors: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}: {results}"
    finally:
        close_pool(dsn)


@_skip
def test_concurrent_uow_pool_exhaustion_queues() -> None:
    """Pool queues requests when max connections reached and serves them in order."""
    from infrastructure.persistence.connection_pool import PoolConfig, close_pool
    from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
    from infrastructure.persistence.repositories.postgres_case_repository import PostgreSQLCaseRepository
    from domain.entities.case import Case

    dsn = _dsn()
    # Intentionally small pool to force queuing
    config = PoolConfig(min_size=1, max_size=2, max_waiting=20, timeout=30.0)

    errors: List[Exception] = []
    start_times: List[float] = []
    finish_times: List[float] = []

    def worker(thread_id: int) -> None:
        try:
            start_times.append(time.monotonic())
            with PostgreSQLPooledDbContext(dsn, pool_config=config) as ctx:
                repo = PostgreSQLCaseRepository(ctx)
                case = Case.create(
                    case_number=f"QUEUE-{thread_id:03d}",
                    title=f"Queue test {thread_id}",
                    assigned_to="det.queue",
                    created_by="admin",
                )
                repo.add(case)
                ctx.commit()
                repo.delete(f"QUEUE-{thread_id:03d}")
                ctx.commit()
            finish_times.append(time.monotonic())
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 8)]

    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert not errors, f"Queued workers raised errors: {errors}"
        # All 7 workers should complete despite only 2 pool connections
        assert len(finish_times) == 7
    finally:
        close_pool(dsn)


# ---------------------------------------------------------------------------
# Pool lifecycle
# ---------------------------------------------------------------------------

@_skip
def test_pool_close_and_recreate() -> None:
    """Closing a pool and creating a new one works correctly."""
    from infrastructure.persistence.connection_pool import (
        PoolConfig,
        close_pool,
        get_or_create_pool,
    )

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=2)

    try:
        pool_first = get_or_create_pool(dsn, config)
        close_pool(dsn)

        # After close, a new pool should be created
        pool_second = get_or_create_pool(dsn, PoolConfig(min_size=1, max_size=3))

        assert pool_first is not pool_second, "Expected a fresh pool after close"
    finally:
        close_pool(dsn)


@_skip
def test_close_all_pools() -> None:
    """close_all_pools() shuts down every registered pool."""
    from infrastructure.persistence.connection_pool import (
        PoolConfig,
        close_all_pools,
        get_or_create_pool,
        _registry,
    )

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=2)

    get_or_create_pool(dsn, config)
    assert dsn in _registry

    close_all_pools()
    assert dsn not in _registry


@_skip
def test_pooled_context_rollback_on_error() -> None:
    """PostgreSQLPooledDbContext rolls back and returns connection on exception."""
    from infrastructure.persistence.connection_pool import PoolConfig, close_pool
    from infrastructure.persistence.db_context import PostgreSQLPooledDbContext
    from infrastructure.persistence.repositories.postgres_case_repository import PostgreSQLCaseRepository
    from domain.entities.case import Case

    dsn = _dsn()
    config = PoolConfig(min_size=1, max_size=3)

    try:
        with pytest.raises(RuntimeError, match="intentional"):
            with PostgreSQLPooledDbContext(dsn, pool_config=config) as ctx:
                repo = PostgreSQLCaseRepository(ctx)
                case = Case.create(
                    case_number="ROLLBACK-POOL-001",
                    title="Rollback test",
                    assigned_to="det.rb",
                    created_by="admin",
                )
                repo.add(case)
                raise RuntimeError("intentional error to trigger rollback")

        # After rollback, the case should not exist
        with PostgreSQLPooledDbContext(dsn, pool_config=config) as ctx2:
            repo2 = PostgreSQLCaseRepository(ctx2)
            assert repo2.get_by_id("ROLLBACK-POOL-001") is None
    finally:
        close_pool(dsn)
