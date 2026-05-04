"""tests/application/test_phase11_lead_service.py

Phase 11 — InvestigativeLeadService unit tests.

Tests the full service layer using InMemory repositories and a FixedClock,
with no real database required.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pytest

from application.dtos.lead_dto import CreateLeadDto, LeadDto, UpdateLeadDto
from application.interfaces.i_lead_repository import IInvestigativeLeadRepository
from application.interfaces.i_lead_service import IInvestigativeLeadService
from application.services.lead_service import InvestigativeLeadService
from domain.entities.investigative_lead import InvestigativeLead
from domain.exceptions.domain_exceptions import DomainValidationError
from infrastructure.persistence.repositories.lead_repository import (
    InMemoryInvestigativeLeadRepository,
)
from infrastructure.time.fixed_clock import FixedClock


# ---------------------------------------------------------------------------
# Stubs / fakes
# ---------------------------------------------------------------------------

class _FakeAudit:
    def __init__(self):
        self.events: List[dict] = []

    def log_event(self, **kwargs) -> None:
        self.events.append(kwargs)


_FIXED_TS = datetime(2025, 6, 1, 12, 0, 0)


def _make_service(
    repo: Optional[IInvestigativeLeadRepository] = None,
) -> tuple[InvestigativeLeadService, _FakeAudit, IInvestigativeLeadRepository]:
    audit = _FakeAudit()
    repo = repo or InMemoryInvestigativeLeadRepository()
    clock = FixedClock(_FIXED_TS)
    svc = InvestigativeLeadService(lead_repository=repo, audit_service=audit, clock=clock)
    return svc, audit, repo


# ---------------------------------------------------------------------------
# Interface compliance
# ---------------------------------------------------------------------------

class TestLeadServiceInterface:
    def test_is_subclass_of_interface(self) -> None:
        assert issubclass(InvestigativeLeadService, IInvestigativeLeadService)


# ---------------------------------------------------------------------------
# create_lead
# ---------------------------------------------------------------------------

class TestCreateLead:
    def test_create_returns_lead_dto(self) -> None:
        svc, _, _ = _make_service()
        dto = svc.create_lead(CreateLeadDto(case_number="CASE-001", name="Phone Records", created_by="alice"))
        assert isinstance(dto, LeadDto)
        assert dto.case_number == "CASE-001"
        assert dto.name == "Phone Records"
        assert dto.completed is False

    def test_create_assigns_sequential_id(self) -> None:
        svc, _, _ = _make_service()
        dto1 = svc.create_lead(CreateLeadDto(case_number="C", name="Lead A", created_by="alice"))
        dto2 = svc.create_lead(CreateLeadDto(case_number="C", name="Lead B", created_by="alice"))
        assert int(dto1.lead_id) < int(dto2.lead_id)

    def test_create_stores_clock_timestamps(self) -> None:
        svc, _, _ = _make_service()
        dto = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        assert dto.created_at == _FIXED_TS
        assert dto.modified_at == _FIXED_TS

    def test_create_strips_whitespace_from_name(self) -> None:
        svc, _, _ = _make_service()
        dto = svc.create_lead(CreateLeadDto(case_number="C", name="  Whitespace  ", created_by="alice"))
        assert dto.name == "Whitespace"

    def test_create_stores_source_and_description(self) -> None:
        svc, _, _ = _make_service()
        dto = svc.create_lead(
            CreateLeadDto(case_number="C", name="L", source="CCTV", description="Footage from 5th Ave", created_by="alice")
        )
        assert dto.source == "CCTV"
        assert dto.description == "Footage from 5th Ave"

    def test_create_logs_audit_event(self) -> None:
        svc, audit, _ = _make_service()
        svc.create_lead(CreateLeadDto(case_number="C", name="Lead", created_by="alice"))
        assert any(e["event_type"] == "LEAD_CREATED" for e in audit.events)

    def test_create_raises_for_empty_case_number(self) -> None:
        svc, _, _ = _make_service()
        with pytest.raises(DomainValidationError):
            svc.create_lead(CreateLeadDto(case_number="", name="L", created_by="alice"))

    def test_create_raises_for_blank_name(self) -> None:
        svc, _, _ = _make_service()
        with pytest.raises(DomainValidationError):
            svc.create_lead(CreateLeadDto(case_number="C", name="   ", created_by="alice"))


# ---------------------------------------------------------------------------
# get_lead / get_leads_for_case
# ---------------------------------------------------------------------------

class TestGetLead:
    def test_get_lead_returns_dto(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        found = svc.get_lead(created.lead_id)
        assert found is not None
        assert found.lead_id == created.lead_id

    def test_get_lead_returns_none_for_missing(self) -> None:
        svc, _, _ = _make_service()
        assert svc.get_lead("9999") is None

    def test_get_leads_for_case_returns_all(self) -> None:
        svc, _, _ = _make_service()
        svc.create_lead(CreateLeadDto(case_number="C-1", name="A", created_by="alice"))
        svc.create_lead(CreateLeadDto(case_number="C-1", name="B", created_by="alice"))
        svc.create_lead(CreateLeadDto(case_number="C-2", name="X", created_by="alice"))
        leads = svc.get_leads_for_case("C-1")
        assert len(leads) == 2
        assert all(l.case_number == "C-1" for l in leads)

    def test_get_leads_for_case_empty_list(self) -> None:
        svc, _, _ = _make_service()
        assert svc.get_leads_for_case("NOPE") == []


# ---------------------------------------------------------------------------
# update_lead
# ---------------------------------------------------------------------------

class TestUpdateLead:
    def test_update_name(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="Old", created_by="alice"))
        updated = svc.update_lead(UpdateLeadDto(lead_id=created.lead_id, name="New"))
        assert updated.name == "New"

    def test_update_source_and_description(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        updated = svc.update_lead(
            UpdateLeadDto(lead_id=created.lead_id, source="Informant", description="Tip off")
        )
        assert updated.source == "Informant"
        assert updated.description == "Tip off"

    def test_update_logs_audit_event(self) -> None:
        svc, audit, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.update_lead(UpdateLeadDto(lead_id=created.lead_id, name="Updated"))
        assert any(e["event_type"] == "LEAD_UPDATED" for e in audit.events)

    def test_update_raises_for_unknown_id(self) -> None:
        svc, _, _ = _make_service()
        with pytest.raises(DomainValidationError):
            svc.update_lead(UpdateLeadDto(lead_id="999", name="X"))

    def test_update_raises_for_blank_name(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        with pytest.raises(DomainValidationError):
            svc.update_lead(UpdateLeadDto(lead_id=created.lead_id, name="  "))


# ---------------------------------------------------------------------------
# complete_lead / reopen_lead
# ---------------------------------------------------------------------------

class TestCompleteLead:
    def test_complete_sets_flag_and_completed_by(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        completed = svc.complete_lead(created.lead_id, completed_by="bob")
        assert completed.completed is True
        assert completed.completed_by == "bob"
        assert completed.completed_at is not None

    def test_complete_logs_audit_event(self) -> None:
        svc, audit, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.complete_lead(created.lead_id, completed_by="bob")
        assert any(e["event_type"] == "LEAD_COMPLETED" for e in audit.events)

    def test_complete_raises_for_already_completed(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.complete_lead(created.lead_id, completed_by="bob")
        with pytest.raises(DomainValidationError):
            svc.complete_lead(created.lead_id, completed_by="bob")

    def test_complete_raises_for_unknown_id(self) -> None:
        svc, _, _ = _make_service()
        with pytest.raises(DomainValidationError):
            svc.complete_lead("9999", completed_by="bob")


class TestReopenLead:
    def test_reopen_clears_completed_flag(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.complete_lead(created.lead_id, completed_by="bob")
        reopened = svc.reopen_lead(created.lead_id, reopened_by="alice")
        assert reopened.completed is False
        assert reopened.completed_at is None
        assert reopened.completed_by is None

    def test_reopen_logs_audit_event(self) -> None:
        svc, audit, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.complete_lead(created.lead_id, completed_by="bob")
        svc.reopen_lead(created.lead_id, reopened_by="alice")
        assert any(e["event_type"] == "LEAD_REOPENED" for e in audit.events)

    def test_reopen_raises_for_open_lead(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        with pytest.raises(DomainValidationError):
            svc.reopen_lead(created.lead_id, reopened_by="alice")

    def test_reopen_raises_for_unknown_id(self) -> None:
        svc, _, _ = _make_service()
        with pytest.raises(DomainValidationError):
            svc.reopen_lead("9999", reopened_by="alice")


# ---------------------------------------------------------------------------
# delete_lead
# ---------------------------------------------------------------------------

class TestDeleteLead:
    def test_delete_removes_lead(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.delete_lead(created.lead_id, deleted_by="alice")
        assert svc.get_lead(created.lead_id) is None

    def test_delete_logs_audit_event(self) -> None:
        svc, audit, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.delete_lead(created.lead_id, deleted_by="alice")
        assert any(e["event_type"] == "LEAD_DELETED" for e in audit.events)

    def test_delete_raises_for_unknown_id(self) -> None:
        svc, _, _ = _make_service()
        with pytest.raises(DomainValidationError):
            svc.delete_lead("9999", deleted_by="alice")


# ---------------------------------------------------------------------------
# get_open_leads_for_case
# ---------------------------------------------------------------------------

class TestGetOpenLeads:
    def test_returns_only_open_leads(self) -> None:
        svc, _, _ = _make_service()
        l1 = svc.create_lead(CreateLeadDto(case_number="C", name="Open", created_by="alice"))
        l2 = svc.create_lead(CreateLeadDto(case_number="C", name="Closed", created_by="alice"))
        svc.complete_lead(l2.lead_id, completed_by="bob")
        open_leads = svc.get_open_leads_for_case("C")
        assert len(open_leads) == 1
        assert open_leads[0].lead_id == l1.lead_id

    def test_returns_empty_when_all_completed(self) -> None:
        svc, _, _ = _make_service()
        created = svc.create_lead(CreateLeadDto(case_number="C", name="L", created_by="alice"))
        svc.complete_lead(created.lead_id, completed_by="bob")
        assert svc.get_open_leads_for_case("C") == []
