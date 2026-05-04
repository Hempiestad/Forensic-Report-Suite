"""Integration tests for Phase 3.2b — database query performance indexes.

Validates that:
- SQLite migration v4 creates all expected indexes
- SQLite index migration is idempotent (re-running is safe)
- PostgreSQL schema init creates all expected indexes (env-gated)
- Common query paths (status filter, date range, case_number lookup) are
  covered by an index (verified via SQLite EXPLAIN QUERY PLAN)
"""
from __future__ import annotations

import os
import tempfile
from typing import List

import pytest

FORENSIC_PG_DSN = os.getenv("FORENSIC_PG_DSN")
_skip_pg = pytest.mark.skipif(not FORENSIC_PG_DSN, reason="FORENSIC_PG_DSN not set")

# Expected index names — must exist after schema init on both providers
EXPECTED_INDEXES = [
    "idx_cases_status",
    "idx_cases_created_at",
    "idx_cases_assigned_to",
    "idx_reports_case_number",
    "idx_reports_status",
    "idx_reports_created_at",
    "idx_audit_case_number",
    "idx_audit_case_event",
    "idx_audit_timestamp",
    "idx_templates_category",
    "idx_templates_published",
    "idx_notifications_recipient",
    "idx_notifications_case_number",
    "idx_notifications_is_read",
    "idx_legal_processes_case_number",
    "idx_legal_processes_status",
    "idx_legal_processes_due_date",
    "idx_court_dates_case_number",
    "idx_court_dates_court_date",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sqlite_index_names(conn) -> List[str]:
    """Return all user-defined index names in the SQLite database."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()
    return [row[0] for row in rows]


def _sqlite_ctx():
    from infrastructure.persistence.db_context import SQLiteDbContext

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return SQLiteDbContext(tmp.name)


# ---------------------------------------------------------------------------
# SQLite — migration v4 creates all expected indexes
# ---------------------------------------------------------------------------

def test_sqlite_migration_v4_creates_indexes() -> None:
    """SQLite schema migration v4 creates all 19 performance indexes."""
    ctx = _sqlite_ctx()
    try:
        conn = ctx.connection  # triggers full migration including v4
        created = _sqlite_index_names(conn)

        missing = [idx for idx in EXPECTED_INDEXES if idx not in created]
        assert not missing, f"Missing SQLite indexes after migration v4: {missing}"
    finally:
        ctx.close()


def test_sqlite_schema_version_is_9() -> None:
    """Schema versions table records version 10 after full migration."""
    ctx = _sqlite_ctx()
    try:
        conn = ctx.connection
        row = conn.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        assert int(row["v"]) == 10
    finally:
        ctx.close()


def test_sqlite_migration_v4_idempotent() -> None:
    """Opening the same DB twice does not raise (CREATE INDEX IF NOT EXISTS is safe)."""
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    from infrastructure.persistence.db_context import SQLiteDbContext

    ctx1 = SQLiteDbContext(tmp.name)
    _ = ctx1.connection  # apply migrations
    ctx1.close()

    ctx2 = SQLiteDbContext(tmp.name)
    _ = ctx2.connection  # should not fail — version already at 4, no re-migration
    ctx2.close()


def test_sqlite_incremental_migration_from_v3() -> None:
    """A database at schema v3 is upgraded to v4 with indexes on next open."""
    import sqlite3
    import tempfile

    from infrastructure.persistence.db_context import SQLiteDbContext

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    # Manually build a v3-state database (tables present, no indexes, version=3)
    raw = sqlite3.connect(tmp.name)
    raw.row_factory = sqlite3.Row
    raw.execute(
        "CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    raw.execute("INSERT INTO schema_versions(version) VALUES (1)")
    raw.execute("INSERT INTO schema_versions(version) VALUES (2)")
    raw.execute("INSERT INTO schema_versions(version) VALUES (3)")
    # Create the tables that v3 migration would have created
    raw.execute(
        "CREATE TABLE IF NOT EXISTS cases (case_number TEXT PRIMARY KEY, title TEXT, assigned_to TEXT, created_by TEXT, status TEXT, created_at TEXT, modified_at TEXT)"
    )
    raw.execute(
        "CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, case_number TEXT, status TEXT, created_at TEXT, modified_at TEXT)"
    )
    raw.execute(
        "CREATE TABLE IF NOT EXISTS audit_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, case_number TEXT, event_type TEXT, performed_by TEXT, timestamp TEXT, previous_hash TEXT, entry_hash TEXT)"
    )
    raw.execute(
        "CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY, name TEXT UNIQUE, category TEXT, html_content TEXT, is_published INTEGER, is_default INTEGER, is_favorite INTEGER, version_number INTEGER, usage_count INTEGER, created_at TEXT, modified_at TEXT)"
    )
    raw.execute(
        "CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, notification_type TEXT, recipient_username TEXT, title TEXT, message TEXT, case_number TEXT, is_read INTEGER, is_dismissed INTEGER, created_at TEXT)"
    )
    raw.execute(
        "CREATE TABLE IF NOT EXISTS legal_processes (id INTEGER PRIMARY KEY, case_number TEXT, process_type TEXT, status TEXT, due_date TEXT, created_at TEXT)"
    )
    raw.execute(
        "CREATE TABLE IF NOT EXISTS court_dates (id INTEGER PRIMARY KEY, case_number TEXT, date_type TEXT, court_date TEXT, created_at TEXT)"
    )
    raw.commit()
    raw.close()

    # Now open with SQLiteDbContext — should detect v3 and apply v4 through v10
    ctx = SQLiteDbContext(tmp.name)
    conn = ctx.connection

    row = conn.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
    assert int(row["v"]) == 10

    created = _sqlite_index_names(conn)
    missing = [idx for idx in EXPECTED_INDEXES if idx not in created]
    assert not missing, f"Missing indexes after incremental upgrade from v3: {missing}"

    ctx.close()


# ---------------------------------------------------------------------------
# SQLite — EXPLAIN QUERY PLAN confirms index usage
# ---------------------------------------------------------------------------

def test_sqlite_cases_status_query_uses_index() -> None:
    """EXPLAIN QUERY PLAN shows idx_cases_status is used for status filter."""
    ctx = _sqlite_ctx()
    try:
        conn = ctx.connection
        plan_rows = conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM cases WHERE status = 'OPEN'"
        ).fetchall()
        # sqlite3.Row columns for EXPLAIN QUERY PLAN: id, parent, notused, detail
        plan_text = " ".join(str(v) for row in plan_rows for v in row).upper()
        assert "IDX_CASES_STATUS" in plan_text, (
            f"Expected idx_cases_status in query plan, got: {plan_text}"
        )
    finally:
        ctx.close()


def test_sqlite_audit_case_event_composite_index_used() -> None:
    """EXPLAIN QUERY PLAN shows composite idx_audit_case_event is used."""
    ctx = _sqlite_ctx()
    try:
        conn = ctx.connection
        plan_rows = conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM audit_entries "
            "WHERE case_number = 'X' AND event_type = 'CREATED'"
        ).fetchall()
        plan_text = " ".join(str(v) for row in plan_rows for v in row).upper()
        assert "IDX_AUDIT_CASE_EVENT" in plan_text, (
            f"Expected idx_audit_case_event in query plan, got: {plan_text}"
        )
    finally:
        ctx.close()


def test_sqlite_legal_processes_due_date_index_used() -> None:
    """EXPLAIN QUERY PLAN shows idx_legal_processes_due_date is used for overdue queries."""
    ctx = _sqlite_ctx()
    try:
        conn = ctx.connection
        plan_rows = conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM legal_processes WHERE due_date < '2026-01-01'"
        ).fetchall()
        plan_text = " ".join(str(v) for row in plan_rows for v in row).upper()
        assert "IDX_LEGAL_PROCESSES_DUE_DATE" in plan_text, (
            f"Expected idx_legal_processes_due_date in query plan, got: {plan_text}"
        )
    finally:
        ctx.close()


def test_sqlite_court_dates_range_query_uses_index() -> None:
    """EXPLAIN QUERY PLAN shows idx_court_dates_court_date is used for date range."""
    ctx = _sqlite_ctx()
    try:
        conn = ctx.connection
        plan_rows = conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM court_dates "
            "WHERE court_date BETWEEN '2026-01-01' AND '2026-12-31'"
        ).fetchall()
        plan_text = " ".join(str(v) for row in plan_rows for v in row).upper()
        assert "IDX_COURT_DATES_COURT_DATE" in plan_text, (
            f"Expected idx_court_dates_court_date in query plan, got: {plan_text}"
        )
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# PostgreSQL — index creation (env-gated)
# ---------------------------------------------------------------------------

@_skip_pg
def test_postgres_creates_all_indexes() -> None:
    """PostgreSQL schema init creates all 19 performance indexes."""
    from infrastructure.persistence.db_context import PostgreSQLDbContext

    with PostgreSQLDbContext(FORENSIC_PG_DSN) as ctx:  # type: ignore[arg-type]
        with ctx.connection.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'idx_%'"
            )
            rows = cur.fetchall()
            created = [row["indexname"] for row in rows]

        missing = [idx for idx in EXPECTED_INDEXES if idx not in created]
        assert not missing, f"Missing PostgreSQL indexes: {missing}"


@_skip_pg
def test_postgres_index_creation_idempotent() -> None:
    """Opening PostgreSQLDbContext twice does not raise (CREATE INDEX IF NOT EXISTS)."""
    from infrastructure.persistence.db_context import PostgreSQLDbContext

    with PostgreSQLDbContext(FORENSIC_PG_DSN):  # type: ignore[arg-type]
        pass  # first open — creates tables + indexes

    with PostgreSQLDbContext(FORENSIC_PG_DSN):  # type: ignore[arg-type]
        pass  # second open — IF NOT EXISTS prevents errors
