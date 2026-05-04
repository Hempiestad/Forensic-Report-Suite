"""tests/application/test_legal_workflow_bridge.py - Integration tests for legacy bridge."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest

from application.dtos.legal_workflow_dto import CreateLegalProcessDto
from application.integrations.legal_workflow_bridge import LegalWorkflowBridge
from application.interfaces.i_case_repository import ICaseRepository
from application.services.legal_workflow_service import LegalWorkflowService
from domain.entities.case import Case


class InMemoryCaseRepository(ICaseRepository):
    def __init__(self) -> None:
        self._items: Dict[str, Case] = {}

    def get_by_id(self, entity_id: str) -> Optional[Case]:
        return None

    def get_all(self) -> List[Case]:
        return list(self._items.values())

    def add(self, entity: Case) -> None:
        self._items[entity.case_number] = entity

    def update(self, entity: Case) -> None:
        self._items[entity.case_number] = entity

    def delete(self, entity_id: str) -> None:
        self._items.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._items

    def get_by_case_number(self, case_number: str) -> Optional[Case]:
        return self._items.get(case_number)

    def get_by_status(self, status) -> List[Case]:
        return [c for c in self._items.values() if c.status == status]

    def get_assigned_to(self, username: str) -> List[Case]:
        return [c for c in self._items.values() if c.assigned_to == username]

    def search(self, query: str) -> List[Case]:
        return []


class StubAuditService:
    def __init__(self) -> None:
        self.events: List[dict] = []

    def log(self, case_number: str, event_type: str, performed_by: str, details=None) -> None:
        self.events.append({"type": event_type, "case_number": case_number, "performed_by": performed_by})

    def log_legal_process_added(self, case_number: str, performed_by: str, process_type: str) -> None:
        self.events.append({"type": "LEGAL_PROCESS_ADDED", "case_number": case_number, "performed_by": performed_by})


class MockDatabaseManager:
    """Mock database manager for dual-write testing."""

    def __init__(self) -> None:
        self.legal_processes: Dict[str, dict] = {}

    @property
    def conn(self):
        return self

    def execute(self, query: str, params=None):
        # Mock SQL execution
        if "UPDATE legal_processes" in query:
            # For testing, just track that update was called
            self.legal_processes["last_update"] = {"query": query, "params": params}
        return self

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def bridge_with_service() -> tuple[LegalWorkflowBridge, LegalWorkflowService, InMemoryCaseRepository]:
    repo = InMemoryCaseRepository()
    case = Case.create("CASE-700", "Bridge Test", "det.smith", "admin")
    repo.add(case)
    audit = StubAuditService()
    service = LegalWorkflowService(repo, audit)  # type: ignore[arg-type]

    # Bridge with mock database (dual-write mode)
    db_mock = MockDatabaseManager()
    bridge = LegalWorkflowBridge(service, db_mock, enable_legacy=True)

    return bridge, service, repo


def test_bridge_mark_investigator_approved(bridge_with_service: tuple) -> None:
    """Test bridge delegates to service and writes to legacy DB."""
    bridge, service, repo = bridge_with_service
    case_number = "CASE-700"

    # Create process through service
    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="warrant", created_by="admin", due_date=None),
        "admin",
    )

    # Mark approved through bridge
    result = bridge.mark_investigator_approved(
        case_number=case_number,
        process_id=process.process_id,
        approved_by="investigator",
        approved_date="2026-04-24",
    )

    assert result is True
    assert "last_update" in bridge._db.legal_processes


def test_bridge_full_approval_workflow(bridge_with_service: tuple) -> None:
    """Test bridge coordinates full approval workflow (investigator→attorney→judicial)."""
    bridge, service, repo = bridge_with_service
    case_number = "CASE-700"

    # Create process
    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="subpoena", created_by="admin", due_date=None),
        "admin",
    )

    # Chain of approvals through bridge
    assert bridge.mark_investigator_approved(case_number, process.process_id, "investigator") is True
    assert bridge.mark_state_attorney_approved(case_number, process.process_id, "attorney") is True
    assert bridge.mark_judicial_approval(
        case_number, process.process_id, "judge", court_name="District Court"
    ) is True

    # Verify service layer reflects approvals
    status = service.calculate_sla_status(process.process_id)
    assert status["is_fully_approved"] is True


def test_bridge_mark_sent_to_provider(bridge_with_service: tuple) -> None:
    """Test bridge handles sent_to_provider with SLA calculation."""
    bridge, service, repo = bridge_with_service
    case_number = "CASE-700"

    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="warrant", created_by="admin", due_date=None),
        "admin",
    )

    result = bridge.mark_sent_to_provider(
        case_number=case_number,
        process_id=process.process_id,
        sent_by="admin",
        sent_date="2026-04-24",
        transmission_method="email",
        expected_response_days=10,
    )

    assert result is True
    service.mark_sent(case_number, process.process_id, "admin")  # Also mark in service


def test_bridge_provider_acknowledgment_flow(bridge_with_service: tuple) -> None:
    """Test bridge coordinates provider acknowledgment and completion."""
    bridge, service, repo = bridge_with_service
    case_number = "CASE-700"

    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="subpoena", created_by="admin", due_date=None),
        "admin",
    )

    # Provider acknowledgment
    result = bridge.mark_provider_acknowledged(
        case_number=case_number,
        process_id=process.process_id,
        acknowledged_by="provider",
        acknowledged_date="2026-04-25",
    )
    assert result is True

    # Provider completion
    result = bridge.mark_provider_completed(
        case_number=case_number,
        process_id=process.process_id,
        completed_by="provider",
        completed_date="2026-04-26",
    )
    assert result is True


def test_bridge_no_legacy_database(bridge_with_service: tuple) -> None:
    """Test bridge works without legacy database (legacy disabled)."""
    bridge, service, repo = bridge_with_service
    case_number = "CASE-700"

    # Disable legacy database
    bridge._enable_legacy = False
    bridge._db = None

    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="warrant", created_by="admin", due_date=None),
        "admin",
    )

    # Should still work (writes to service only)
    result = bridge.mark_investigator_approved(case_number, process.process_id, "investigator")
    assert result is True

    # Service should reflect change
    status = service.calculate_sla_status(process.process_id)
    assert status["is_fully_approved"] is False  # Only one approval, not all three
