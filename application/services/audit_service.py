"""application/services/audit_service.py - Audit service implementation scaffold."""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.dtos.audit_dto import AuditEntryDto
from application.interfaces.i_audit_repository import IAuditRepository
from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_clock import IClock
from application.services._clock import DefaultClock
from domain.entities.audit_entry import AuditEntry


class AuditService(IAuditService):
    """Centralised audit writer/reader with chain verification."""

    def __init__(self, audit_repository: IAuditRepository, clock: Optional[IClock] = None) -> None:
        self._audits = audit_repository
        self._clock = clock or DefaultClock()

    def log(
        self,
        case_number: str,
        event_type: str,
        performed_by: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        previous = self._audits.get_last_entry_for_case(case_number)
        previous_hash = previous.entry_hash if previous is not None else "0" * 64
        entry = AuditEntry.create(
            case_number=case_number,
            event_type=event_type,
            performed_by=performed_by,
            details=details or {},
            previous_hash=previous_hash,
        )
        entry.timestamp = self._clock.utcnow()
        entry.recompute_hash()
        self._audits.add(entry)

    def get_entries_for_case(self, case_number: str) -> List[AuditEntryDto]:
        return [self._to_dto(e) for e in self._audits.get_for_case(case_number)]

    def get_recent_entries(self, limit: int = 50) -> List[AuditEntryDto]:
        return [self._to_dto(e) for e in self._audits.get_recent(limit=limit)]

    def verify_chain_integrity(self, case_number: str) -> bool:
        entries = self._audits.get_for_case(case_number)
        previous_hash = "0" * 64
        for entry in entries:
            if entry.previous_hash != previous_hash:
                return False
            if not entry.verify_integrity():
                return False
            previous_hash = entry.entry_hash
        return True

    def get_entries_by_event_type(self, event_type: str) -> List[AuditEntryDto]:
        all_entries = self._audits.get_all()
        return [
            self._to_dto(e) for e in all_entries
            if e.event_type == event_type
        ]

    def get_entries_by_date_range(
        self,
        case_number: str,
        start: datetime,
        end: datetime,
    ) -> List[AuditEntryDto]:
        entries = self._audits.get_for_case(case_number)
        return [
            self._to_dto(e) for e in entries
            if e.timestamp is not None and start <= e.timestamp <= end
        ]

    def get_statistics(self, case_number: str) -> Dict[str, Any]:
        entries = self._audits.get_for_case(case_number)
        if not entries:
            return {
                "total": 0,
                "by_event_type": {},
                "by_actor": {},
                "first_entry_at": None,
                "last_entry_at": None,
            }
        timestamps = [e.timestamp for e in entries if e.timestamp]
        return {
            "total": len(entries),
            "by_event_type": dict(Counter(e.event_type for e in entries)),
            "by_actor": dict(Counter(e.performed_by for e in entries)),
            "first_entry_at": min(timestamps) if timestamps else None,
            "last_entry_at": max(timestamps) if timestamps else None,
        }

    def export_to_csv(self, case_number: str) -> str:
        entries = self._audits.get_for_case(case_number)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["entry_id", "event_type", "performed_by", "timestamp",
             "details", "previous_hash", "entry_hash"]
        )
        for e in entries:
            writer.writerow([
                str(e.id) if e.id is not None else "",
                e.event_type,
                e.performed_by,
                e.timestamp.isoformat() if e.timestamp else "",
                json.dumps(dict(e.details)),
                e.previous_hash or "",
                e.entry_hash or "",
            ])
        return buf.getvalue()

    def export_to_json(self, case_number: str) -> str:
        entries = self._audits.get_for_case(case_number)
        data = [
            {
                "entry_id": str(e.id) if e.id is not None else "",
                "event_type": e.event_type,
                "performed_by": e.performed_by,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "details": dict(e.details),
                "previous_hash": e.previous_hash,
                "entry_hash": e.entry_hash,
            }
            for e in entries
        ]
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def _to_dto(entry: AuditEntry) -> AuditEntryDto:
        return AuditEntryDto(
            entry_id=str(entry.id) if entry.id is not None else "",
            case_number=entry.case_number,
            event_type=entry.event_type,
            performed_by=entry.performed_by,
            timestamp=entry.timestamp,
            details=dict(entry.details),
            previous_hash=entry.previous_hash,
            entry_hash=entry.entry_hash,
        )

