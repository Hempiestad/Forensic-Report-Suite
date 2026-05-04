"""infrastructure/persistence/repositories - Repository implementations."""

from infrastructure.persistence.repositories.case_repository import InMemoryCaseRepository
from infrastructure.persistence.repositories.report_repository import InMemoryReportRepository
from infrastructure.persistence.repositories.template_repository import InMemoryTemplateRepository
from infrastructure.persistence.repositories.notification_repository import InMemoryNotificationRepository
from infrastructure.persistence.repositories.audit_repository import InMemoryAuditRepository
from infrastructure.persistence.repositories.legal_process_repository import InMemoryLegalProcessRepository
from infrastructure.persistence.repositories.court_date_repository import InMemoryCourtDateRepository
from infrastructure.persistence.repositories.evidence_repository import InMemoryEvidenceRepository
from infrastructure.persistence.repositories.note_repository import InMemoryNoteRepository
from infrastructure.persistence.repositories.sqlite_case_repository import SQLiteCaseRepository
from infrastructure.persistence.repositories.sqlite_report_repository import SQLiteReportRepository
from infrastructure.persistence.repositories.sqlite_audit_repository import SQLiteAuditRepository
from infrastructure.persistence.repositories.sqlite_template_repository import SQLiteTemplateRepository
from infrastructure.persistence.repositories.sqlite_notification_repository import SQLiteNotificationRepository
from infrastructure.persistence.repositories.sqlite_legal_process_repository import SQLiteLegalProcessRepository
from infrastructure.persistence.repositories.sqlite_court_date_repository import SQLiteCourtDateRepository
from infrastructure.persistence.repositories.sqlite_evidence_repository import SQLiteEvidenceRepository
from infrastructure.persistence.repositories.sqlite_note_repository import SQLiteNoteRepository
from infrastructure.persistence.repositories.postgres_case_repository import PostgreSQLCaseRepository
from infrastructure.persistence.repositories.postgres_report_repository import PostgreSQLReportRepository
from infrastructure.persistence.repositories.postgres_audit_repository import PostgreSQLAuditRepository
from infrastructure.persistence.repositories.postgres_template_repository import PostgreSQLTemplateRepository
from infrastructure.persistence.repositories.postgres_notification_repository import PostgreSQLNotificationRepository
from infrastructure.persistence.repositories.postgres_legal_process_repository import PostgreSQLLegalProcessRepository
from infrastructure.persistence.repositories.postgres_court_date_repository import PostgreSQLCourtDateRepository
from infrastructure.persistence.repositories.postgres_evidence_repository import PostgreSQLEvidenceRepository
from infrastructure.persistence.repositories.postgres_note_repository import PostgreSQLNoteRepository
from infrastructure.persistence.repositories.lead_repository import InMemoryInvestigativeLeadRepository
from infrastructure.persistence.repositories.sqlite_lead_repository import SQLiteInvestigativeLeadRepository
from infrastructure.persistence.repositories.postgres_lead_repository import PostgreSQLInvestigativeLeadRepository

__all__ = [
    "InMemoryCaseRepository",
    "InMemoryReportRepository",
    "InMemoryTemplateRepository",
    "InMemoryNotificationRepository",
    "InMemoryAuditRepository",
    "InMemoryLegalProcessRepository",
    "InMemoryCourtDateRepository",
    "InMemoryEvidenceRepository",
    "InMemoryNoteRepository",
    "SQLiteCaseRepository",
    "SQLiteReportRepository",
    "SQLiteAuditRepository",
    "SQLiteTemplateRepository",
    "SQLiteNotificationRepository",
    "SQLiteLegalProcessRepository",
    "SQLiteCourtDateRepository",
    "SQLiteEvidenceRepository",
    "SQLiteNoteRepository",
    "PostgreSQLCaseRepository",
    "PostgreSQLReportRepository",
    "PostgreSQLAuditRepository",
    "PostgreSQLTemplateRepository",
    "PostgreSQLNotificationRepository",
    "PostgreSQLLegalProcessRepository",
    "PostgreSQLCourtDateRepository",
    "PostgreSQLEvidenceRepository",
    "PostgreSQLNoteRepository",
]
