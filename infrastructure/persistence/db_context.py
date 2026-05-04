"""Database contexts for infrastructure persistence adapters."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SQLiteDbContext:
    """Thin SQLite context wrapper for repository adapters."""

    SCHEMA_VERSION = 10

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._open()
        return self._conn

    def _open(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        row = conn.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
        current_version = int(row["v"] or 0)

        for version in range(current_version + 1, self.SCHEMA_VERSION + 1):
            self._apply_migration(version)
            conn.execute("INSERT INTO schema_versions(version) VALUES (?)", (version,))
            conn.commit()

    def _apply_migration(self, version: int) -> None:
        if version == 1:
            self._migration_v1()
        elif version == 2:
            self._migration_v2()
        elif version == 3:
            self._migration_v3()
        elif version == 4:
            self._migration_v4()
        elif version == 5:
            self._migration_v5()
        elif version == 6:
            self._migration_v6()
        elif version == 7:
            self._migration_v7()
        elif version == 8:
            self._migration_v8()
        elif version == 9:
            self._migration_v9()
        elif version == 10:
            self._migration_v10()

    def _migration_v1(self) -> None:
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_number TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                created_by TEXT NOT NULL,
                status TEXT NOT NULL,
                examiner_id TEXT,
                review_comments TEXT,
                trial_date TEXT,
                sentencing_date TEXT,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                modified_by TEXT,
                peer_reviewers TEXT
            )
            """
        )

    def _migration_v2(self) -> None:
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY,
                case_number TEXT NOT NULL,
                report_html TEXT,
                report_html_encrypted BLOB,
                status TEXT NOT NULL,
                appendices TEXT,
                final_pdf_hash TEXT,
                finalized_by TEXT,
                finalized_at TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT,
                modified_at TEXT NOT NULL,
                modified_by TEXT,
                UNIQUE(case_number)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL,
                event_type TEXT NOT NULL,
                performed_by TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                html_content TEXT NOT NULL,
                description TEXT,
                is_published INTEGER NOT NULL DEFAULT 0,
                is_default INTEGER NOT NULL DEFAULT 0,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                version_number INTEGER NOT NULL DEFAULT 1,
                tags TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT,
                parent_template_id INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT,
                modified_at TEXT NOT NULL,
                modified_by TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY,
                notification_type TEXT NOT NULL,
                recipient_username TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                case_number TEXT,
                related_entity_id TEXT,
                is_read INTEGER NOT NULL DEFAULT 0,
                is_dismissed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                read_at TEXT,
                dismissed_at TEXT
            )
            """
        )

    def _migration_v3(self) -> None:
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_processes (
                id INTEGER PRIMARY KEY,
                case_number TEXT NOT NULL,
                process_type TEXT NOT NULL,
                provider TEXT,
                status TEXT NOT NULL,
                submission_date TEXT,
                due_date TEXT,
                expiration_date TEXT,
                received_date TEXT,
                analysis_start_date TEXT,
                completed_date TEXT,
                investigator_approved INTEGER NOT NULL DEFAULT 0,
                investigator_approved_by TEXT,
                investigator_approved_at TEXT,
                state_attorney_approved INTEGER NOT NULL DEFAULT 0,
                state_attorney_approved_by TEXT,
                state_attorney_approved_at TEXT,
                judicial_approved INTEGER NOT NULL DEFAULT 0,
                judicial_approved_by TEXT,
                judicial_approved_at TEXT,
                notes TEXT,
                ndr INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS court_dates (
                id INTEGER PRIMARY KEY,
                case_number TEXT NOT NULL,
                date_type TEXT NOT NULL,
                court_date TEXT NOT NULL,
                location TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

    def _migration_v4(self) -> None:
        """Add performance indexes for common query patterns."""
        conn = self.connection
        # cases — filter by status, time-range queries, assigned workload
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases (status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_assigned_to ON cases (assigned_to)")
        # reports — filter by status, time ranges
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_case_number ON reports (case_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports (created_at)")
        # audit_entries — case lookup, composite event filter, chronological queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_case_number ON audit_entries (case_number)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_case_event "
            "ON audit_entries (case_number, event_type)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_entries (timestamp)")
        # templates — category browsing, published filter (tables created in v5; skip if not ready)
        # These indexes are re-created in _migration_v5 once the tables exist.
        # notifications — inbox queries, unread filter
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_recipient "
            "ON notifications (recipient_username)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_case_number "
            "ON notifications (case_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_is_read "
            "ON notifications (is_read)"
        )
        # legal_processes — case lookup, overdue/due-soon filters
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_processes_case_number "
            "ON legal_processes (case_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_processes_status "
            "ON legal_processes (status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_processes_due_date "
            "ON legal_processes (due_date)"
        )
        # court_dates — case lookup, upcoming date range queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_court_dates_case_number "
            "ON court_dates (case_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_court_dates_court_date "
            "ON court_dates (court_date)"
        )

    def _migration_v5(self) -> None:
        """Create template system tables (templates, template_versions, template_placeholders)."""
        conn = self.connection
        conn.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                html_content TEXT NOT NULL,
                description TEXT,
                is_published INTEGER DEFAULT 0,
                is_default INTEGER DEFAULT 0,
                is_favorite INTEGER DEFAULT 0,
                version_number INTEGER DEFAULT 1,
                tags TEXT DEFAULT '[]',
                usage_count INTEGER DEFAULT 0,
                last_used_at TEXT,
                parent_template_id INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                modified_by TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS template_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                html_content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (template_id) REFERENCES templates (id) ON DELETE CASCADE
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS template_placeholders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                placeholder_type TEXT DEFAULT 'string',
                is_required INTEGER DEFAULT 1,
                default_value TEXT,
                sample_value TEXT,
                validation_pattern TEXT,
                help_text TEXT,
                FOREIGN KEY (template_id) REFERENCES templates (id) ON DELETE CASCADE,
                UNIQUE (template_id, name)
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(name)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_templates_published ON templates(is_published)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_template_versions_tmpl ON template_versions(template_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_template_ph_tmpl ON template_placeholders(template_id)')

    def _migration_v6(self) -> None:
        """Create evidence table for the Evidence entity + supporting indexes."""
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY,
                case_number TEXT NOT NULL,
                evidence_item_number TEXT NOT NULL,
                item_type TEXT NOT NULL,
                physical_description TEXT,
                digital_make TEXT,
                digital_model TEXT,
                digital_type TEXT,
                digital_serial_number TEXT,
                digital_storage_size TEXT,
                password TEXT,
                status TEXT NOT NULL DEFAULT 'NOT_IMAGED',
                imaged_date TEXT,
                analyzed_date TEXT,
                completed_date TEXT,
                evidence_found TEXT,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_case_number ON evidence (case_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence (status)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_case_item "
            "ON evidence (case_number, evidence_item_number)"
        )

    def _migration_v7(self) -> None:
        """Create notes table for the Note entity + supporting indexes."""
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                case_number TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT,
                modified_by TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notes_case_number ON notes (case_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes (created_at)"
        )

    def _migration_v8(self) -> None:
        """Create investigative_leads table + supporting indexes."""
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investigative_leads (
                id INTEGER PRIMARY KEY,
                case_number TEXT NOT NULL,
                name TEXT NOT NULL,
                source TEXT,
                description TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                completed_by TEXT,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_leads_case_number ON investigative_leads (case_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_leads_completed ON investigative_leads (completed)"
        )

    def _migration_v9(self) -> None:
        """Create template_versions and template_placeholders child tables."""
        conn = self.connection
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS template_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                html_content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                notes TEXT,
                UNIQUE(template_id, version_number)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tmpl_versions_template_id ON template_versions (template_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS template_placeholders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                placeholder_type TEXT NOT NULL DEFAULT 'string',
                is_required INTEGER NOT NULL DEFAULT 1,
                default_value TEXT,
                sample_value TEXT,
                UNIQUE(template_id, name)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tmpl_placeholders_template_id ON template_placeholders (template_id)"
        )

    def _migration_v10(self) -> None:
        """Extend notes table with status, tags, note_type, priority, and approval columns."""
        conn = self.connection
        _add = [
            "ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
            "ALTER TABLE notes ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE notes ADD COLUMN note_type TEXT",
            "ALTER TABLE notes ADD COLUMN priority TEXT",
            "ALTER TABLE notes ADD COLUMN approved_by TEXT",
            "ALTER TABLE notes ADD COLUMN approved_at TEXT",
            "ALTER TABLE notes ADD COLUMN approval_comments TEXT",
        ]
        for stmt in _add:
            try:
                conn.execute(stmt)
            except Exception:  # column already exists on re-run
                pass
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notes_status ON notes (status)"
        )

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SQLiteDbContext":
        _ = self.connection
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


class PostgreSQLDbContext:
    """Thin PostgreSQL context wrapper for repository adapters."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: Optional[Any] = None

    @property
    def connection(self) -> Any:
        if self._conn is None:
            self._open()
        return self._conn

    def _open(self) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires psycopg. Install with 'pip install psycopg[binary]'."
            ) from exc

        self._conn = psycopg.connect(self._dsn, row_factory=dict_row, autocommit=False)
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        _initialize_postgres_schema(self._conn)

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "PostgreSQLDbContext":
        _ = self.connection
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


class PostgreSQLPooledDbContext:
    """PostgreSQL context that borrows connections from a shared psycopg_pool pool.

    Unlike PostgreSQLDbContext (which holds one long-lived connection), this
    context acquires a connection from a pool, runs operations within a single
    transaction, then returns the connection automatically when the context
    manager exits or when close() is called.

    Lifecycle:
        1. ``__enter__`` / first ``connection`` access → borrow from pool.
        2. Repositories execute queries on the borrowed connection.
        3. ``commit()`` / ``rollback()`` flush the transaction.
        4. ``close()`` / ``__exit__`` returns the connection to the pool.

    Usage:
        config = PoolConfig(min_size=2, max_size=10)
        ctx = PostgreSQLPooledDbContext(dsn, pool_config=config)
        with ctx:
            repo = SQLiteCaseRepository(ctx)  # same interface as non-pooled
            repo.add(entity)
        # connection returned to pool automatically

    Sharing a pool across requests:
        The underlying ConnectionPool is stored in the singleton registry in
        connection_pool.py and is shared across all contexts with the same DSN.
    """

    def __init__(
        self,
        dsn: str,
        pool_config: Optional[Any] = None,
    ) -> None:
        """
        Args:
            dsn: PostgreSQL connection string.
            pool_config: PoolConfig instance.  Defaults to PoolConfig() (min=2, max=10).
        """
        from infrastructure.persistence.connection_pool import PoolConfig, get_or_create_pool

        self._dsn = dsn
        self._pool_config: Any = pool_config or PoolConfig()
        self._pool = get_or_create_pool(dsn, self._pool_config)
        self._conn: Optional[Any] = None      # borrowed connection (or None if not held)
        self._pool_conn: Optional[Any] = None  # pool-managed wrapper (has .connection)

    @property
    def connection(self) -> Any:
        """Borrow a connection from the pool (idempotent within a context)."""
        if self._conn is None:
            self._acquire()
        return self._conn  # type: ignore[return-value]

    def _acquire(self) -> None:
        """Acquire a connection from the pool and run schema initialization."""
        self._pool_conn = self._pool.getconn()
        self._conn = self._pool_conn
        # Only initialize schema once per pool lifetime by detecting tables
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist (idempotent CREATE TABLE IF NOT EXISTS)."""
        _initialize_postgres_schema(self._conn)

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    def rollback(self) -> None:
        if self._conn is not None:
            self._conn.rollback()

    def close(self) -> None:
        """Return the connection back to the pool."""
        if self._pool_conn is not None:
            try:
                self._pool.putconn(self._pool_conn)
            except Exception:  # pragma: no cover
                logger.exception("Error returning connection to pool.")
            finally:
                self._pool_conn = None
                self._conn = None

    def stats(self) -> dict:
        """Return current pool statistics."""
        from infrastructure.persistence.connection_pool import pool_stats
        return pool_stats(self._dsn)

    def __enter__(self) -> "PostgreSQLPooledDbContext":
        _ = self.connection  # ensure connection is acquired
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()


# ---------------------------------------------------------------------------
# Shared schema initialiser — used by both pooled and non-pooled contexts
# ---------------------------------------------------------------------------

def _initialize_postgres_schema(conn: Any) -> None:
    """Run CREATE TABLE IF NOT EXISTS for every managed table.

    This is idempotent and safe to call on every connection, so pooled contexts
    can call it cheaply on borrow without full schema inspection overhead.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_number TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                created_by TEXT NOT NULL,
                status TEXT NOT NULL,
                examiner_id TEXT,
                review_comments TEXT,
                trial_date TIMESTAMP NULL,
                sentencing_date TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL,
                modified_at TIMESTAMP NOT NULL,
                modified_by TEXT,
                peer_reviewers JSONB
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id BIGINT PRIMARY KEY,
                case_number TEXT NOT NULL UNIQUE,
                report_html TEXT,
                report_html_encrypted BYTEA,
                status TEXT NOT NULL,
                appendices JSONB,
                final_pdf_hash TEXT,
                finalized_by TEXT,
                finalized_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL,
                created_by TEXT,
                modified_at TIMESTAMP NOT NULL,
                modified_by TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_entries (
                id BIGSERIAL PRIMARY KEY,
                case_number TEXT NOT NULL,
                event_type TEXT NOT NULL,
                performed_by TEXT NOT NULL,
                details JSONB,
                timestamp TIMESTAMP NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                html_content TEXT NOT NULL,
                description TEXT,
                is_published BOOLEAN NOT NULL DEFAULT FALSE,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
                version_number INTEGER NOT NULL DEFAULT 1,
                tags JSONB,
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TIMESTAMP NULL,
                parent_template_id BIGINT NULL,
                created_at TIMESTAMP NOT NULL,
                created_by TEXT,
                modified_at TIMESTAMP NOT NULL,
                modified_by TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id BIGINT PRIMARY KEY,
                notification_type TEXT NOT NULL,
                recipient_username TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                case_number TEXT,
                related_entity_id TEXT,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL,
                read_at TIMESTAMP NULL,
                dismissed_at TIMESTAMP NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_processes (
                id BIGINT PRIMARY KEY,
                case_number TEXT NOT NULL,
                process_type TEXT NOT NULL,
                provider TEXT,
                status TEXT NOT NULL,
                submission_date TIMESTAMP NULL,
                due_date TIMESTAMP NULL,
                expiration_date TIMESTAMP NULL,
                received_date TIMESTAMP NULL,
                analysis_start_date TIMESTAMP NULL,
                completed_date TIMESTAMP NULL,
                investigator_approved BOOLEAN NOT NULL DEFAULT FALSE,
                investigator_approved_by TEXT,
                investigator_approved_at TIMESTAMP NULL,
                state_attorney_approved BOOLEAN NOT NULL DEFAULT FALSE,
                state_attorney_approved_by TEXT,
                state_attorney_approved_at TIMESTAMP NULL,
                judicial_approved BOOLEAN NOT NULL DEFAULT FALSE,
                judicial_approved_by TEXT,
                judicial_approved_at TIMESTAMP NULL,
                notes TEXT,
                ndr BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS court_dates (
                id BIGINT PRIMARY KEY,
                case_number TEXT NOT NULL,
                date_type TEXT NOT NULL,
                court_date TIMESTAMP NOT NULL,
                location TEXT,
                notes TEXT,
                created_at TIMESTAMP NOT NULL
            )
            """
        )
        # ── Performance indexes ─────────────────────────────────────────────
        # cases
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cases_status ON cases (status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cases_assigned_to ON cases (assigned_to)"
        )
        # reports
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_case_number ON reports (case_number)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports (created_at)"
        )
        # audit_entries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_case_number ON audit_entries (case_number)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_case_event "
            "ON audit_entries (case_number, event_type)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_entries (timestamp)"
        )
        # templates
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_templates_category ON templates (category)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_templates_published ON templates (is_published)"
        )
        # notifications
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_recipient "
            "ON notifications (recipient_username)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_case_number "
            "ON notifications (case_number)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_is_read "
            "ON notifications (is_read)"
        )
        # legal_processes
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_processes_case_number "
            "ON legal_processes (case_number)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_processes_status "
            "ON legal_processes (status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_processes_due_date "
            "ON legal_processes (due_date)"
        )
        # court_dates
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_court_dates_case_number "
            "ON court_dates (case_number)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_court_dates_court_date "
            "ON court_dates (court_date)"
        )
    conn.commit()

