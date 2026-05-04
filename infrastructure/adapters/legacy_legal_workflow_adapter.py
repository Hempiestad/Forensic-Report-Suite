"""infrastructure/adapters/legacy_legal_workflow_adapter.py - Bridge legacy helpers to new service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from application.dtos.legal_workflow_dto import CreateLegalProcessDto
from application.interfaces.i_legal_workflow_service import ILegalWorkflowService


class LegacyLegalWorkflowAdapter:
    """
    Bridges legacy legal_workflow_helpers.py into the new ILegalWorkflowService.

    Provides compatibility shim so existing code can delegate to the new domain model
    without immediate refactoring.
    """

    def __init__(self, legal_workflow_service: ILegalWorkflowService) -> None:
        self._service = legal_workflow_service

    def mark_investigator_approved(self, case_number: str, process_id: str, approved_by: str) -> bool:
        try:
            self._service.approve_as_investigator(case_number, process_id, approved_by)
            return True
        except Exception:
            return False

    def mark_state_attorney_approved(self, case_number: str, process_id: str, approved_by: str) -> bool:
        try:
            self._service.approve_as_state_attorney(case_number, process_id, approved_by)
            return True
        except Exception:
            return False

    def mark_judicial_approval(self, case_number: str, process_id: str, approved_by: str) -> bool:
        try:
            self._service.approve_as_judicial(case_number, process_id, approved_by)
            return True
        except Exception:
            return False

    def mark_sent_to_provider(
        self, case_number: str, process_id: str, sent_by: str, expected_response_days: Optional[int] = None
    ) -> bool:
        try:
            self._service.mark_sent(case_number, process_id, sent_by)
            return True
        except Exception:
            return False

    def mark_provider_acknowledged(self, case_number: str, process_id: str, acknowledged_by: str) -> bool:
        try:
            self._service.mark_acknowledged(case_number, process_id, acknowledged_by)
            return True
        except Exception:
            return False

    def mark_provider_completed(self, case_number: str, process_id: str, completed_by: str) -> bool:
        try:
            self._service.mark_completed(case_number, process_id, completed_by)
            return True
        except Exception:
            return False
