"""infrastructure/persistence/unit_of_work.py - Unit of Work pattern implementation."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from infrastructure.persistence.repositories import (
    InMemoryAuditRepository,
    InMemoryCaseRepository,
    InMemoryCourtDateRepository,
    InMemoryEvidenceRepository,
    InMemoryLegalProcessRepository,
    InMemoryNoteRepository,
    InMemoryNotificationRepository,
    InMemoryReportRepository,
    InMemoryInvestigativeLeadRepository,
    PostgreSQLCaseRepository,
    PostgreSQLReportRepository,
    PostgreSQLAuditRepository,
    PostgreSQLTemplateRepository,
    PostgreSQLNotificationRepository,
    PostgreSQLLegalProcessRepository,
    PostgreSQLCourtDateRepository,
    PostgreSQLEvidenceRepository,
    PostgreSQLNoteRepository,
    PostgreSQLInvestigativeLeadRepository,
    SQLiteCaseRepository,
    SQLiteEvidenceRepository,
    SQLiteNoteRepository,
    SQLiteInvestigativeLeadRepository,
    SQLiteReportRepository,
    SQLiteAuditRepository,
    SQLiteTemplateRepository,
    SQLiteNotificationRepository,
    SQLiteLegalProcessRepository,
    SQLiteCourtDateRepository,
    InMemoryTemplateRepository,
)
from infrastructure.persistence.db_context import PostgreSQLDbContext, PostgreSQLPooledDbContext, SQLiteDbContext

if TYPE_CHECKING:
    from application.interfaces.i_audit_repository import IAuditRepository
    from application.interfaces.i_case_repository import ICaseRepository
    from application.interfaces.i_court_date_repository import ICourtDateRepository
    from application.interfaces.i_evidence_repository import IEvidenceRepository
    from application.interfaces.i_legal_process_repository import ILegalProcessRepository
    from application.interfaces.i_note_repository import INoteRepository
    from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
    from application.interfaces.i_notification_repository import INotificationRepository
    from application.interfaces.i_report_repository import IReportRepository
    from application.interfaces.i_unit_of_work import IUnitOfWork
    from application.interfaces.i_template_repository import ITemplateRepository


class UnitOfWork:
    """
    Unit of Work implementation coordinating multiple repository writes.

    Phase 3 uses in-memory repositories.
    Phase 3.2 (sqlite/postgres) wires real persistence.
    Phase 3.2a (pool) adds pooled PostgreSQL connections via PostgreSQLPooledDbContext.
    """

    def __init__(
        self,
        provider: str = "memory",
        sqlite_db_path: str | None = None,
        postgres_dsn: str | None = None,
        db_context: SQLiteDbContext | PostgreSQLDbContext | PostgreSQLPooledDbContext | None = None,
        use_sqlite_for_cases: bool = False,
        pool_config: Optional[object] = None,
        case_repo: "ICaseRepository | None" = None,
        report_repo: "IReportRepository | None" = None,
        template_repo: "ITemplateRepository | None" = None,
        notification_repo: "INotificationRepository | None" = None,
        audit_repo: "IAuditRepository | None" = None,
        legal_process_repo: "ILegalProcessRepository | None" = None,
        court_date_repo: "ICourtDateRepository | None" = None,
        evidence_repo: "IEvidenceRepository | None" = None,
        note_repo: "INoteRepository | None" = None,
        lead_repo: "IInvestigativeLeadRepository | None" = None,
    ) -> None:
        """Initialize with optional custom repositories (for testing).

        Args:
            provider: One of ``"memory"``, ``"sqlite"``, or ``"postgres"``.
            sqlite_db_path: Path to SQLite database file (provider="sqlite").
            postgres_dsn: PostgreSQL connection string (provider="postgres").
                Falls back to ``FORENSIC_PG_DSN`` environment variable.
            db_context: Pre-created db context.  When supplied the *provider*
                and *postgres_dsn*/*sqlite_db_path* arguments are ignored.
            use_sqlite_for_cases: Legacy flag — forces SQLiteCaseRepository
                when a SQLiteDbContext is supplied via *db_context*.
            pool_config: PoolConfig instance for PostgreSQL connection pooling.
                When supplied with provider="postgres", a pooled context is used
                instead of a single direct connection.  Ignored for other providers.
            *_repo: Optional pre-built repository overrides (for testing).
        """
        self._db_context = db_context
        using_postgres = False
        using_sqlite = False

        default_case_repo = InMemoryCaseRepository()
        if case_repo is None:
            if use_sqlite_for_cases and isinstance(db_context, SQLiteDbContext):
                default_case_repo = SQLiteCaseRepository(db_context)
            elif provider == "sqlite":
                sqlite_ctx = db_context if isinstance(db_context, SQLiteDbContext) else SQLiteDbContext(
                    sqlite_db_path or "forensic_reports_encrypted.db"
                )
                self._db_context = sqlite_ctx
                default_case_repo = SQLiteCaseRepository(sqlite_ctx)
                using_sqlite = True
            elif provider == "postgres":
                resolved_dsn = postgres_dsn or os.getenv("FORENSIC_PG_DSN")
                if not resolved_dsn:
                    raise ValueError(
                        "postgres_dsn is required when provider='postgres' (or set FORENSIC_PG_DSN)."
                    )
                if db_context is not None and isinstance(
                    db_context, (PostgreSQLDbContext, PostgreSQLPooledDbContext)
                ):
                    pg_ctx = db_context
                elif pool_config is not None:
                    # Use connection pool when pool_config provided
                    pg_ctx = PostgreSQLPooledDbContext(resolved_dsn, pool_config=pool_config)
                else:
                    pg_ctx = PostgreSQLDbContext(resolved_dsn)
                self._db_context = pg_ctx
                default_case_repo = PostgreSQLCaseRepository(pg_ctx)
                using_postgres = True
            elif provider != "memory":
                raise ValueError("Unsupported provider. Use one of: memory, sqlite, postgres.")

        self._cases = case_repo or default_case_repo  # type: ignore[arg-type]
        _pg_ctx_types = (PostgreSQLDbContext, PostgreSQLPooledDbContext)

        if report_repo is not None:
            self._reports = report_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._reports = SQLiteReportRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._reports = PostgreSQLReportRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._reports = InMemoryReportRepository()  # type: ignore[arg-type]

        if template_repo is not None:
            self._templates = template_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._templates = SQLiteTemplateRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._templates = PostgreSQLTemplateRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._templates = InMemoryTemplateRepository()  # type: ignore[arg-type]

        if notification_repo is not None:
            self._notifications = notification_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._notifications = SQLiteNotificationRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._notifications = PostgreSQLNotificationRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._notifications = InMemoryNotificationRepository()  # type: ignore[arg-type]
        if audit_repo is not None:
            self._audits = audit_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._audits = SQLiteAuditRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._audits = PostgreSQLAuditRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._audits = InMemoryAuditRepository()  # type: ignore[arg-type]
        if legal_process_repo is not None:
            self._legal_processes = legal_process_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._legal_processes = SQLiteLegalProcessRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._legal_processes = PostgreSQLLegalProcessRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._legal_processes = InMemoryLegalProcessRepository()  # type: ignore[arg-type]
        if court_date_repo is not None:
            self._court_dates = court_date_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._court_dates = SQLiteCourtDateRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._court_dates = PostgreSQLCourtDateRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._court_dates = InMemoryCourtDateRepository()  # type: ignore[arg-type]

        if evidence_repo is not None:
            self._evidence = evidence_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._evidence = SQLiteEvidenceRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._evidence = PostgreSQLEvidenceRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._evidence = InMemoryEvidenceRepository()  # type: ignore[arg-type]

        if note_repo is not None:
            self._notes = note_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._notes = SQLiteNoteRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._notes = PostgreSQLNoteRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._notes = InMemoryNoteRepository()  # type: ignore[arg-type]

        if lead_repo is not None:
            self._leads = lead_repo
        elif using_sqlite and isinstance(self._db_context, SQLiteDbContext):
            self._leads = SQLiteInvestigativeLeadRepository(self._db_context)  # type: ignore[arg-type]
        elif using_postgres and isinstance(self._db_context, _pg_ctx_types):
            self._leads = PostgreSQLInvestigativeLeadRepository(self._db_context)  # type: ignore[arg-type]
        else:
            self._leads = InMemoryInvestigativeLeadRepository()  # type: ignore[arg-type]

    @property
    def cases(self) -> ICaseRepository:
        return self._cases

    @property
    def reports(self) -> IReportRepository:
        return self._reports

    @property
    def templates(self) -> ITemplateRepository:
        return self._templates

    @property
    def notifications(self) -> INotificationRepository:
        return self._notifications

    @property
    def audits(self) -> IAuditRepository:
        return self._audits

    @property
    def legal_processes(self) -> ILegalProcessRepository:
        return self._legal_processes

    @property
    def court_dates(self) -> "ICourtDateRepository":
        return self._court_dates

    @property
    def evidence(self) -> "IEvidenceRepository":
        return self._evidence

    @property
    def notes(self) -> "INoteRepository":
        return self._notes

    @property
    def leads(self) -> "IInvestigativeLeadRepository":
        return self._leads

    def commit(self) -> None:
        """Commit all pending changes. Phase 3: no-op for in-memory. Phase 3.2: actual DB commit."""
        if self._db_context is not None:
            self._db_context.commit()

    def rollback(self) -> None:
        """Rollback all pending changes. Phase 3: no-op for in-memory. Phase 3.2: actual DB rollback."""
        if self._db_context is not None:
            self._db_context.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
