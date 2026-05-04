"""application/integrations/legal_workflow_bridge.py - Coordinates legacy and new service layers."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from application.interfaces.i_legal_workflow_service import ILegalWorkflowService
    from infrastructure.adapters.legacy_legal_workflow_adapter import LegacyLegalWorkflowAdapter


class LegalWorkflowBridge:
    """
    Coordinates between legacy database-direct code and new service layer.
    
    During Phase 2 migration, both paths run in parallel:
    1. New path: Service layer with audit trail and typed entities
    2. Legacy path: Direct database operations (for backward compatibility)
    
    In Phase 3, legacy path will be fully removed.
    """

    def __init__(self, service: ILegalWorkflowService, db_manager=None, enable_legacy: bool = True) -> None:
        """
        Initialize bridge.
        
        Args:
            service: New ILegalWorkflowService implementation
            db_manager: Legacy database manager (optional, for dual-write mode)
            enable_legacy: If True, also write to legacy database for compatibility
        """
        self._service = service
        self._db = db_manager
        self._enable_legacy = enable_legacy

    def mark_investigator_approved(
        self, case_number: str, process_id: str, approved_by: str, approved_date: Optional[str] = None
    ) -> bool:
        """
        Mark legal process as approved by investigator.
        
        Writes to new service layer and optionally legacy database.
        """
        try:
            # Write to new service layer
            self._service.approve_as_investigator(case_number, process_id, approved_by)

            # Dual-write to legacy database if enabled
            if self._enable_legacy and self._db:
                with self._db.conn:
                    self._db.conn.execute(
                        """UPDATE legal_processes 
                           SET investigator_approved_date = ?, investigator_name = ?, status = 'in_progress'
                           WHERE id = ?""",
                        (approved_date or datetime.now().isoformat(), approved_by, process_id),
                    )

            logger.info(f"Legal process {process_id} approved by investigator {approved_by}")
            return True
        except Exception as e:
            logger.error(f"Error marking investigator approval: {e}", exc_info=True)
            return False

    def mark_state_attorney_approved(
        self, case_number: str, process_id: str, approved_by: str, approved_date: Optional[str] = None
    ) -> bool:
        """Mark legal process as approved by state attorney."""
        try:
            self._service.approve_as_state_attorney(case_number, process_id, approved_by)

            if self._enable_legacy and self._db:
                with self._db.conn:
                    self._db.conn.execute(
                        """UPDATE legal_processes 
                           SET state_attorney_approved_date = ?, state_attorney_name = ?
                           WHERE id = ?""",
                        (approved_date or datetime.now().isoformat(), approved_by, process_id),
                    )

            logger.info(f"Legal process {process_id} approved by state attorney {approved_by}")
            return True
        except Exception as e:
            logger.error(f"Error marking state attorney approval: {e}", exc_info=True)
            return False

    def mark_judicial_approval(
        self,
        case_number: str,
        process_id: str,
        approved_by: str,
        approval_date: Optional[str] = None,
        court_name: Optional[str] = None,
    ) -> bool:
        """Mark legal process as judicially approved."""
        try:
            self._service.approve_as_judicial(case_number, process_id, approved_by)

            if self._enable_legacy and self._db:
                with self._db.conn:
                    self._db.conn.execute(
                        """UPDATE legal_processes 
                           SET judicial_approval_date = ?, court_name = ?, judge_name = ?
                           WHERE id = ?""",
                        (approval_date or datetime.now().isoformat(), court_name or "", approved_by, process_id),
                    )

            logger.info(f"Legal process {process_id} judicially approved by {approved_by}")
            return True
        except Exception as e:
            logger.error(f"Error marking judicial approval: {e}", exc_info=True)
            return False

    def mark_sent_to_provider(
        self,
        case_number: str,
        process_id: str,
        sent_by: str,
        sent_date: Optional[str] = None,
        transmission_method: Optional[str] = None,
        expected_response_days: Optional[int] = None,
    ) -> bool:
        """Mark legal process as sent to provider."""
        try:
            self._service.mark_sent(case_number, process_id, sent_by)

            if self._enable_legacy and self._db:
                sent_dt = (
                    datetime.fromisoformat(sent_date)
                    if sent_date and "T" in sent_date
                    else (datetime.strptime(sent_date, "%Y-%m-%d") if sent_date else datetime.now())
                )
                sla_due_date = None
                if expected_response_days:
                    sla_due_date = (sent_dt + timedelta(days=expected_response_days)).strftime("%Y-%m-%d")

                with self._db.conn:
                    self._db.conn.execute(
                        """UPDATE legal_processes 
                           SET sent_to_provider_date = ?, transmission_method = ?, 
                               expected_response_days = ?, sla_due_date = ?, status = 'in_progress'
                           WHERE id = ?""",
                        (sent_dt.isoformat(), transmission_method or "email", expected_response_days, sla_due_date, process_id),
                    )

            logger.info(f"Legal process {process_id} sent to provider by {sent_by}")
            return True
        except Exception as e:
            logger.error(f"Error marking sent to provider: {e}", exc_info=True)
            return False

    def mark_provider_acknowledged(
        self, case_number: str, process_id: str, acknowledged_by: str, acknowledged_date: Optional[str] = None
    ) -> bool:
        """Mark provider acknowledgment."""
        try:
            self._service.mark_acknowledged(case_number, process_id, acknowledged_by)

            if self._enable_legacy and self._db:
                with self._db.conn:
                    self._db.conn.execute(
                        """UPDATE legal_processes 
                           SET acknowledged_date = ?, status = 'acknowledged'
                           WHERE id = ?""",
                        (acknowledged_date or datetime.now().isoformat(), process_id),
                    )

            logger.info(f"Legal process {process_id} acknowledged by {acknowledged_by}")
            return True
        except Exception as e:
            logger.error(f"Error marking provider acknowledged: {e}", exc_info=True)
            return False

    def mark_provider_completed(
        self, case_number: str, process_id: str, completed_by: str, completed_date: Optional[str] = None
    ) -> bool:
        """Mark provider completion."""
        try:
            self._service.mark_completed(case_number, process_id, completed_by)

            if self._enable_legacy and self._db:
                with self._db.conn:
                    self._db.conn.execute(
                        """UPDATE legal_processes 
                           SET completed_date = ?, status = 'completed'
                           WHERE id = ?""",
                        (completed_date or datetime.now().isoformat(), process_id),
                    )

            logger.info(f"Legal process {process_id} completed by {completed_by}")
            return True
        except Exception as e:
            logger.error(f"Error marking provider completed: {e}", exc_info=True)
            return False
