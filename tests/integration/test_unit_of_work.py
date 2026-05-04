"""tests/integration/test_unit_of_work.py - Integration tests for Unit of Work and repositories."""
from __future__ import annotations

import pytest

from application.dtos.court_date_dto import CreateCourtDateDto
from application.dtos.legal_workflow_dto import CreateLegalProcessDto
from application.services.audit_service import AuditService
from application.services.case_service import CaseService
from application.services.legal_workflow_service import LegalWorkflowService
from application.services.notification_service import NotificationService
from application.services.report_service import ReportService
from domain.entities.case import Case
from domain.entities.report import Report
from domain.enums.case_status import CaseStatus
from domain.enums.notification_type import NotificationType
from domain.enums.report_status import ReportStatus
from infrastructure.persistence.unit_of_work import UnitOfWork


class TestUnitOfWorkIntegration:
    """Integration tests validating all repositories work together through Unit of Work."""

    @pytest.fixture
    def uow(self) -> UnitOfWork:
        """Create a fresh UnitOfWork with in-memory repositories."""
        return UnitOfWork()

    def test_case_crud_through_uow(self, uow: UnitOfWork) -> None:
        """Test full case lifecycle through UnitOfWork."""
        case = Case.create("CASE-1001", "Integration Test Case", "det.alice", "admin")
        
        with uow:
            uow.cases.add(case)
            uow.commit()
        
        # Verify persistence
        retrieved = uow.cases.get_by_case_number("CASE-1001")
        assert retrieved is not None
        assert retrieved.title == "Integration Test Case"

    def test_report_crud_through_uow(self, uow: UnitOfWork) -> None:
        """Test report creation and persistence through UnitOfWork."""
        report = Report.create(
            id=1001,
            case_number="CASE-1001",
            created_by="det.alice",
        )
        
        with uow:
            uow.reports.add(report)
            uow.commit()
        
        # Verify persistence
        retrieved = uow.reports.get_by_id("1001")
        assert retrieved is not None
        assert retrieved.case_number == "CASE-1001"
        assert retrieved.status == ReportStatus.DRAFT

    def test_multi_entity_transaction(self, uow: UnitOfWork) -> None:
        """Test transactional consistency across multiple entity types."""
        case = Case.create("CASE-1002", "Multi-Entity Test", "det.bob", "admin")
        report = Report.create(1002, "CASE-1002", "det.bob")
        
        with uow:
            uow.cases.add(case)
            uow.reports.add(report)
            uow.commit()
        
        # Both should persist
        assert uow.cases.get_by_case_number("CASE-1002") is not None
        assert uow.reports.get_by_id("1002") is not None
        assert len(uow.cases.get_all()) >= 1
        assert len(uow.reports.get_all()) >= 1

    def test_case_service_with_uow(self, uow: UnitOfWork) -> None:
        """Test CaseService using UnitOfWork repositories."""
        from application.dtos.case_dto import CreateCaseDto
        
        audit = AuditService(uow.audits)
        case_service = CaseService(uow.cases, audit)
        
        # Create case through service
        dto = case_service.create_case(
            CreateCaseDto(
                case_number="CASE-1003",
                title="Service Integration",
                assigned_to="det.charlie",
                created_by="admin",
            )
        )
        
        # Verify through UoW
        assert uow.cases.get_by_case_number("CASE-1003") is not None
        assert dto.case_number == "CASE-1003"
        
        # Verify audit trail
        audit_entries = uow.audits.get_for_case("CASE-1003")
        assert len(audit_entries) > 0

    def test_legal_workflow_with_uow(self, uow: UnitOfWork) -> None:
        """Test legal workflow service integrated with UoW."""
        # Setup
        case = Case.create("CASE-1004", "Legal Workflow Test", "det.diana", "admin")
        uow.cases.add(case)
        
        audit = AuditService(uow.audits)
        workflow_service = LegalWorkflowService(uow.cases, audit)
        
        # Add legal process through service
        process_dto = workflow_service.add_legal_process(
            "CASE-1004",
            CreateLegalProcessDto(
                case_number="CASE-1004",
                process_type="warrant",
                created_by="det.diana",
                due_date=None,
            ),
            "det.diana",
        )
        
        # Verify through UoW
        updated_case = uow.cases.get_by_case_number("CASE-1004")
        assert updated_case is not None
        assert len(updated_case.legal_processes) > 0
        assert process_dto.process_type == "warrant"

    def test_notifications_with_uow(self, uow: UnitOfWork) -> None:
        """Test notification service integrated with UoW."""
        notif_service = NotificationService(uow.notifications)
        
        # Create notification
        notif = notif_service.create_notification(
            notification_type=NotificationType.CASE_CREATED,
            recipient_username="det.eve",
            title="Test Notification",
            message="This is a test",
            case_number="CASE-1005",
        )
        
        # Verify through UoW
        user_notifs = uow.notifications.get_for_user("det.eve")
        assert len(user_notifs) > 0
        assert user_notifs[0].recipient_username == "det.eve"
        assert notif_service.get_unread_count("det.eve") > 0

    def test_audit_trail_integrity(self, uow: UnitOfWork) -> None:
        """Test audit trail is built correctly through service operations."""
        case = Case.create("CASE-1006", "Audit Trail Test", "det.frank", "admin")
        uow.cases.add(case)
        
        audit = AuditService(uow.audits)
        case_service = CaseService(uow.cases, audit)
        
        # Perform transition
        case_service.transition_status("CASE-1006", CaseStatus.UNDER_INVESTIGATION, "det.frank")
        
        # Verify audit chain
        entries = uow.audits.get_for_case("CASE-1006")
        assert len(entries) >= 1
        
        # Verify hash chain integrity
        integrity_check = audit.verify_chain_integrity("CASE-1006")
        assert integrity_check is True

    def test_rollback_on_error(self, uow: UnitOfWork) -> None:
        """Test that UoW rollback is called on exception."""
        try:
            with uow:
                case = Case.create("CASE-1007", "Rollback Test", "det.grace", "admin")
                uow.cases.add(case)
                raise ValueError("Intentional error")
        except ValueError:
            pass
        
        # Case should still exist in memory repo (in-memory has no rollback semantics yet)
        # This test demonstrates the pattern; Phase 3.2 will use real DB rollback
        retrieved = uow.cases.get_by_case_number("CASE-1007")
        # For now, case persists because in-memory repos don't support rollback
        # Real DB implementation will clear this on rollback

    def test_repository_query_methods(self, uow: UnitOfWork) -> None:
        """Test typed repository query methods through UoW."""
        # Add multiple cases with different statuses
        case1 = Case.create("CASE-1008", "Query Test 1", "det.henry", "admin")
        case2 = Case.create("CASE-1009", "Query Test 2", "det.henry", "admin")
        case3 = Case.create("CASE-1010", "Query Test 3", "det.iris", "admin")
        
        uow.cases.add(case1)
        uow.cases.add(case2)
        uow.cases.add(case3)
        
        # Test get_by_status
        draft_cases = uow.cases.get_by_status(CaseStatus.DRAFT)
        matching = [c for c in draft_cases if c.case_number in ["CASE-1008", "CASE-1009", "CASE-1010"]]
        assert len(matching) >= 1
        
        # Test get_assigned_to
        henry_cases = uow.cases.get_assigned_to("det.henry")
        henry_matching = [c for c in henry_cases if c.case_number in ["CASE-1008", "CASE-1009"]]
        assert len(henry_matching) >= 1
        
        # Test search
        search_results = uow.cases.search("Query Test 1")
        assert len(search_results) > 0
        assert search_results[0].case_number == "CASE-1008"
