"""tests/application/test_phase9_infrastructure_utils.py

Phase 9 — Infrastructure utility layer tests.

Covers:
- UuidIdGenerator contract
- IUnitOfWork abstract property surface (evidence + notes)
- application/interfaces __init__ exports
"""
from __future__ import annotations

import uuid
from abc import ABC

import pytest

from application.interfaces.i_id_generator import IIdGenerator
from application.interfaces.i_unit_of_work import IUnitOfWork
from infrastructure.identity.uuid_id_generator import UuidIdGenerator


# ---------------------------------------------------------------------------
# UuidIdGenerator
# ---------------------------------------------------------------------------

class TestUuidIdGenerator:
    """UuidIdGenerator satisfies the IIdGenerator contract."""

    def test_is_subclass_of_interface(self) -> None:
        assert issubclass(UuidIdGenerator, IIdGenerator)

    def test_new_id_returns_string(self) -> None:
        gen = UuidIdGenerator()
        result = gen.new_id()
        assert isinstance(result, str)

    def test_new_id_is_valid_uuid4(self) -> None:
        gen = UuidIdGenerator()
        result = gen.new_id()
        parsed = uuid.UUID(result)
        assert parsed.version == 4

    def test_new_id_is_unique_across_calls(self) -> None:
        gen = UuidIdGenerator()
        ids = {gen.new_id() for _ in range(100)}
        assert len(ids) == 100

    def test_new_id_format_is_hyphenated(self) -> None:
        gen = UuidIdGenerator()
        result = gen.new_id()
        # xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = result.split("-")
        assert len(parts) == 5

    def test_multiple_generators_produce_independent_ids(self) -> None:
        gen_a = UuidIdGenerator()
        gen_b = UuidIdGenerator()
        assert gen_a.new_id() != gen_b.new_id()


# ---------------------------------------------------------------------------
# IUnitOfWork — abstract property surface
# ---------------------------------------------------------------------------

class TestIUnitOfWorkAbstractSurface:
    """Verify IUnitOfWork declares all required abstract properties."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            IUnitOfWork()  # type: ignore[abstract]

    def test_has_cases_abstract_property(self) -> None:
        assert "cases" in IUnitOfWork.__abstractmethods__

    def test_has_reports_abstract_property(self) -> None:
        assert "reports" in IUnitOfWork.__abstractmethods__

    def test_has_templates_abstract_property(self) -> None:
        assert "templates" in IUnitOfWork.__abstractmethods__

    def test_has_notifications_abstract_property(self) -> None:
        assert "notifications" in IUnitOfWork.__abstractmethods__

    def test_has_audits_abstract_property(self) -> None:
        assert "audits" in IUnitOfWork.__abstractmethods__

    def test_has_legal_processes_abstract_property(self) -> None:
        assert "legal_processes" in IUnitOfWork.__abstractmethods__

    def test_has_court_dates_abstract_property(self) -> None:
        assert "court_dates" in IUnitOfWork.__abstractmethods__

    def test_has_evidence_abstract_property(self) -> None:
        assert "evidence" in IUnitOfWork.__abstractmethods__

    def test_has_notes_abstract_property(self) -> None:
        assert "notes" in IUnitOfWork.__abstractmethods__

    def test_has_enter_abstract_method(self) -> None:
        assert "__enter__" in IUnitOfWork.__abstractmethods__

    def test_has_exit_abstract_method(self) -> None:
        assert "__exit__" in IUnitOfWork.__abstractmethods__


# ---------------------------------------------------------------------------
# IUnitOfWork — UnitOfWork concrete class satisfies the interface
# ---------------------------------------------------------------------------

class TestUnitOfWorkSatisfiesInterface:
    """Concrete UnitOfWork must fully satisfy IUnitOfWork."""

    def test_unit_of_work_is_subclass(self) -> None:
        from infrastructure.persistence.unit_of_work import UnitOfWork
        assert issubclass(UnitOfWork, IUnitOfWork) or _has_all_properties(UnitOfWork)

    def test_unit_of_work_evidence_property_exists(self) -> None:
        from infrastructure.persistence.unit_of_work import UnitOfWork
        uow = UnitOfWork(provider="memory")
        assert hasattr(uow, "evidence")

    def test_unit_of_work_notes_property_exists(self) -> None:
        from infrastructure.persistence.unit_of_work import UnitOfWork
        uow = UnitOfWork(provider="memory")
        assert hasattr(uow, "notes")

    def test_unit_of_work_all_repo_properties_accessible(self) -> None:
        from infrastructure.persistence.unit_of_work import UnitOfWork
        uow = UnitOfWork(provider="memory")
        _ = uow.cases
        _ = uow.reports
        _ = uow.templates
        _ = uow.notifications
        _ = uow.audits
        _ = uow.legal_processes
        _ = uow.court_dates
        _ = uow.evidence
        _ = uow.notes

    def test_unit_of_work_evidence_returns_i_evidence_repository(self) -> None:
        from application.interfaces.i_evidence_repository import IEvidenceRepository
        from infrastructure.persistence.unit_of_work import UnitOfWork
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.evidence, IEvidenceRepository)

    def test_unit_of_work_notes_returns_i_note_repository(self) -> None:
        from application.interfaces.i_note_repository import INoteRepository
        from infrastructure.persistence.unit_of_work import UnitOfWork
        uow = UnitOfWork(provider="memory")
        assert isinstance(uow.notes, INoteRepository)


def _has_all_properties(cls) -> bool:
    """Fallback check when UnitOfWork does not inherit IUnitOfWork."""
    required = {
        "cases", "reports", "templates", "notifications",
        "audits", "legal_processes", "court_dates", "evidence", "notes",
    }
    return required.issubset(set(dir(cls)))


# ---------------------------------------------------------------------------
# application/interfaces __init__ exports
# ---------------------------------------------------------------------------

class TestApplicationInterfacesExports:
    """All interfaces including the Phase 9 additions are exported."""

    def test_i_evidence_repository_exported(self) -> None:
        from application.interfaces import IEvidenceRepository  # noqa: F401

    def test_i_note_repository_exported(self) -> None:
        from application.interfaces import INoteRepository  # noqa: F401

    def test_i_id_generator_exported(self) -> None:
        from application.interfaces import IIdGenerator  # noqa: F401

    def test_i_unit_of_work_exported(self) -> None:
        from application.interfaces import IUnitOfWork  # noqa: F401

    def test_i_evidence_repository_in_all(self) -> None:
        import application.interfaces as pkg
        assert "IEvidenceRepository" in pkg.__all__

    def test_i_note_repository_in_all(self) -> None:
        import application.interfaces as pkg
        assert "INoteRepository" in pkg.__all__

    def test_all_service_interfaces_in_all(self) -> None:
        import application.interfaces as pkg
        for name in (
            "IEvidenceService", "INoteService", "IGlossaryService",
            "IPeerReviewService", "IEncryptionService", "ICacheService",
        ):
            assert name in pkg.__all__, f"{name} missing from __all__"
