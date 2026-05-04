from application.interfaces.i_repository import IRepository
from application.interfaces.i_case_service import ICaseService
from application.interfaces.i_report_service import IReportService
from application.interfaces.i_template_service import ITemplateService
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_notification_service import INotificationService
from application.interfaces.i_legal_workflow_service import ILegalWorkflowService
from application.interfaces.i_evidence_service import IEvidenceService
from application.interfaces.i_peer_review_service import IPeerReviewService
from application.interfaces.i_note_service import INoteService
from application.interfaces.i_glossary_service import IGlossaryService
from application.interfaces.i_encryption_service import IEncryptionService
from application.interfaces.i_unit_of_work import IUnitOfWork
from application.interfaces.i_clock import IClock
from application.interfaces.i_id_generator import IIdGenerator
from application.interfaces.i_cache_service import ICacheService
from application.interfaces.i_case_repository import ICaseRepository
from application.interfaces.i_report_repository import IReportRepository
from application.interfaces.i_template_repository import ITemplateRepository
from application.interfaces.i_notification_repository import INotificationRepository
from application.interfaces.i_audit_repository import IAuditRepository
from application.interfaces.i_legal_process_repository import ILegalProcessRepository
from application.interfaces.i_court_date_repository import ICourtDateRepository
from application.interfaces.i_evidence_repository import IEvidenceRepository
from application.interfaces.i_note_repository import INoteRepository
from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
from application.interfaces.i_lead_service import IInvestigativeLeadService

__all__ = [
    "IRepository",
    "ICaseService",
    "IReportService",
    "ITemplateService",
    "IAuditService",
    "INotificationService",
    "ILegalWorkflowService",
    "IEvidenceService",
    "IPeerReviewService",
    "INoteService",
    "IGlossaryService",
    "IEncryptionService",
    "IUnitOfWork",
    "IClock",
    "IIdGenerator",
    "ICacheService",
    "ICaseRepository",
    "IReportRepository",
    "ITemplateRepository",
    "INotificationRepository",
    "IAuditRepository",
    "ILegalProcessRepository",
    "ICourtDateRepository",
    "IEvidenceRepository",
    "INoteRepository",
    "IInvestigativeLeadRepository",
    "IInvestigativeLeadService",
]
