"""application/interfaces/i_unit_of_work.py - Transaction boundary abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
    from application.interfaces.i_template_repository import ITemplateRepository


class IUnitOfWork(ABC):

    @property
    @abstractmethod
    def cases(self) -> "ICaseRepository":
        """Case repository bound to this transaction."""

    @property
    @abstractmethod
    def reports(self) -> "IReportRepository":
        """Report repository bound to this transaction."""

    @property
    @abstractmethod
    def templates(self) -> "ITemplateRepository":
        """Template repository bound to this transaction."""

    @property
    @abstractmethod
    def notifications(self) -> "INotificationRepository":
        """Notification repository bound to this transaction."""

    @property
    @abstractmethod
    def audits(self) -> "IAuditRepository":
        """Audit repository bound to this transaction."""

    @property
    @abstractmethod
    def legal_processes(self) -> "ILegalProcessRepository":
        """Legal-process repository bound to this transaction."""

    @property
    @abstractmethod
    def court_dates(self) -> "ICourtDateRepository":
        """Court-date repository bound to this transaction."""

    @property
    @abstractmethod
    def evidence(self) -> "IEvidenceRepository":
        """Evidence repository bound to this transaction."""

    @property
    @abstractmethod
    def notes(self) -> "INoteRepository":
        """Note repository bound to this transaction."""

    @property
    @abstractmethod
    def leads(self) -> "IInvestigativeLeadRepository":
        """InvestigativeLead repository bound to this transaction."""

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork":
        """Enter transactional context."""

    @abstractmethod
    def __exit__(self, exc_type, exc, tb) -> None:
        """Exit transactional context, committing or rolling back."""

    @abstractmethod
    def commit(self) -> None:
        """Persist all pending changes atomically."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard all pending changes."""
