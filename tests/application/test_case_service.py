from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from application.dtos.case_dto import CreateCaseDto, UpdateCaseDto
from application.interfaces.i_case_repository import ICaseRepository
from application.services.case_service import CaseService
from domain.entities.case import Case
from domain.enums.case_status import CaseStatus
from domain.exceptions.domain_exceptions import EntityNotFoundError


class InMemoryCaseRepository(ICaseRepository):
    def __init__(self) -> None:
        self._items: Dict[str, Case] = {}

    def get_by_id(self, entity_id: str) -> Optional[Case]:
        return self._items.get(entity_id)

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

    def get_by_status(self, status: CaseStatus) -> List[Case]:
        return [c for c in self._items.values() if c.status == status]

    def get_assigned_to(self, username: str) -> List[Case]:
        return [c for c in self._items.values() if c.assigned_to == username]

    def search(self, query: str) -> List[Case]:
        q = query.lower()
        return [c for c in self._items.values() if q in c.case_number.lower() or q in c.title.lower()]


class StubAuditService:
    def __init__(self) -> None:
        self.events: List[dict] = []

    def log_case_created(self, case_number: str, performed_by: str, data: dict) -> None:
        self.events.append({"type": "CASE_CREATED", "case_number": case_number, "performed_by": performed_by, "data": data})

    def log_case_status_changed(self, case_number: str, performed_by: str, from_status: str, to_status: str) -> None:
        self.events.append(
            {
                "type": "CASE_STATUS_CHANGED",
                "case_number": case_number,
                "performed_by": performed_by,
                "from": from_status,
                "to": to_status,
            }
        )

    def log(self, case_number: str, event_type: str, performed_by: str, details=None) -> None:
        self.events.append(
            {
                "type": event_type,
                "case_number": case_number,
                "performed_by": performed_by,
                "details": details or {},
            }
        )


@pytest.fixture
def case_service() -> CaseService:
    repo = InMemoryCaseRepository()
    audit = StubAuditService()
    return CaseService(repo, audit)  # type: ignore[arg-type]


def test_create_case_emits_audit(case_service: CaseService) -> None:
    dto = CreateCaseDto(
        case_number="CASE-100",
        title="Phone extraction",
        assigned_to="det.jones",
        created_by="admin",
    )

    created = case_service.create_case(dto)

    assert created.case_number == "CASE-100"
    assert created.status == "draft"
    assert case_service._audit.events[0]["type"] == "CASE_CREATED"  # pylint: disable=protected-access


def test_transition_status_updates_case_and_audits(case_service: CaseService) -> None:
    case_service.create_case(
        CreateCaseDto(
            case_number="CASE-200",
            title="Laptop review",
            assigned_to="det.kim",
            created_by="admin",
        )
    )

    updated = case_service.transition_status("CASE-200", CaseStatus.UNDER_INVESTIGATION, "admin")

    assert updated.status == "under_investigation"
    assert any(e["type"] == "CASE_STATUS_CHANGED" for e in case_service._audit.events)  # pylint: disable=protected-access


def test_update_unknown_case_raises(case_service: CaseService) -> None:
    with pytest.raises(EntityNotFoundError):
        case_service.update_case(UpdateCaseDto(case_number="MISSING", title="x", modified_by="admin"))
