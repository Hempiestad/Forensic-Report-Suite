"""infrastructure/persistence/repositories/court_date_repository.py - Court date repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from application.interfaces.i_court_date_repository import ICourtDateRepository
from domain.entities.court_date import CourtDate


class InMemoryCourtDateRepository(ICourtDateRepository):
    """In-memory court date repository for Phase 3 testing. Will be replaced with SQLite adapter.
    
    Note: Court dates are children of Case aggregates and are typically accessed through
    CaseRepository. This repository exists for direct access queries.
    """

    def __init__(self) -> None:
        self._court_dates: dict[str, CourtDate] = {}

    def get_by_id(self, entity_id: str) -> Optional[CourtDate]:
        return self._court_dates.get(entity_id)

    def get_all(self) -> List[CourtDate]:
        return list(self._court_dates.values())

    def add(self, entity: CourtDate) -> None:
        self._court_dates[str(entity.id)] = entity

    def update(self, entity: CourtDate) -> None:
        self._court_dates[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._court_dates.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._court_dates

    def get_for_case(self, case_number: str) -> List[CourtDate]:
        return [c for c in self._court_dates.values() if c.case_number == case_number]

    def get_upcoming(self, days_ahead: int = 90) -> List[CourtDate]:
        """Get court dates within the next N days."""
        now = datetime.utcnow()
        cutoff = datetime.utcnow().replace(hour=23, minute=59, second=59)
        from datetime import timedelta
        cutoff = now + timedelta(days=days_ahead)
        return [c for c in self._court_dates.values() if now <= c.court_date <= cutoff]
