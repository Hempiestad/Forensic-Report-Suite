from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest

from application.dtos.court_date_dto import CreateCourtDateDto
from application.dtos.legal_workflow_dto import CreateLegalProcessDto
from application.interfaces.i_case_repository import ICaseRepository
from application.services.legal_workflow_service import LegalWorkflowService
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus


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


@pytest.fixture
def legal_workflow_service() -> tuple[LegalWorkflowService, InMemoryCaseRepository]:
    repo = InMemoryCaseRepository()
    case = Case.create("CASE-500", "Legal Workflow Test", "det.johnson", "admin")
    repo.add(case)
    audit = StubAuditService()
    service = LegalWorkflowService(repo, audit)  # type: ignore[arg-type]
    return service, repo


def test_add_legal_process(legal_workflow_service: tuple) -> None:
    service, repo = legal_workflow_service
    case_number = "CASE-500"
    due_date = datetime.utcnow() + timedelta(days=30)

    result = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="subpoena", created_by="admin", due_date=due_date),
        "admin",
    )

    assert result.case_number == case_number
    assert result.process_type == "subpoena"
    assert result.due_date == due_date


def test_approval_workflow(legal_workflow_service: tuple) -> None:
    service, repo = legal_workflow_service
    case_number = "CASE-500"

    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="warrant", created_by="admin", due_date=None),
        "admin",
    )

    service.approve_as_investigator(case_number, process.process_id, "investigator")
    service.approve_as_state_attorney(case_number, process.process_id, "attorney")
    service.approve_as_judicial(case_number, process.process_id, "judge")

    status = service.calculate_sla_status(process.process_id)
    assert status["is_fully_approved"] is True


def test_sla_tracking(legal_workflow_service: tuple) -> None:
    service, repo = legal_workflow_service
    case_number = "CASE-500"
    now = datetime.utcnow()
    due_soon = now + timedelta(days=3)

    process = service.add_legal_process(
        case_number,
        CreateLegalProcessDto(case_number=case_number, process_type="subpoena", created_by="admin", due_date=due_soon),
        "admin",
    )

    status = service.calculate_sla_status(process.process_id)
    assert status["is_overdue"] is False
    assert status["days_remaining"] >= 2  # Allow 2-3 days for timing variation


def test_court_dates(legal_workflow_service: tuple) -> None:
    service, repo = legal_workflow_service
    case_number = "CASE-500"
    court_date = datetime.utcnow() + timedelta(days=45)

    result = service.add_court_date(
        case_number,
        CreateCourtDateDto(
            case_number=case_number,
            hearing_type="trial",
            court_date=court_date,
            created_by="admin",
        ),
        "admin",
    )

    assert result.hearing_type == "trial"
    assert result.court_date == court_date

    upcoming = service.get_upcoming_court_dates(case_number)
    assert len(upcoming) == 1
    assert upcoming[0].court_date_id == result.court_date_id
