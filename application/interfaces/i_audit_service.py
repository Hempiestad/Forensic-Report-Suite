"""application/interfaces/i_audit_service.py — Audit trail service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class IAuditService(ABC):

    @abstractmethod
    def log(
        self,
        case_number: str,
        event_type: str,
        performed_by: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write a new tamper-evident audit entry."""

    @abstractmethod
    def get_entries_for_case(self, case_number: str) -> List[object]:
        """Return all audit entries for a specific case."""

    @abstractmethod
    def get_recent_entries(self, limit: int = 50) -> List[object]:
        """Return the most recent N audit entries across all cases."""

    @abstractmethod
    def verify_chain_integrity(self, case_number: str) -> bool:
        """
        Re-verify the hash chain for a case's audit trail.
        Returns True if intact, False if tampering detected.
        """

    @abstractmethod
    def get_entries_by_event_type(self, event_type: str) -> List[object]:
        """Return all audit entries matching the given event type."""

    @abstractmethod
    def get_entries_by_date_range(
        self,
        case_number: str,
        start: datetime,
        end: datetime,
    ) -> List[object]:
        """Return audit entries for a case within a date/time window."""

    @abstractmethod
    def get_statistics(self, case_number: str) -> Dict[str, Any]:
        """
        Return summary statistics for a case's audit trail.
        Keys: total, by_event_type (dict), by_actor (dict), first_entry_at, last_entry_at.
        """

    @abstractmethod
    def export_to_csv(self, case_number: str) -> str:
        """Return audit trail for a case as a CSV string."""

    @abstractmethod
    def export_to_json(self, case_number: str) -> str:
        """Return audit trail for a case as a JSON string."""

    # ── Convenience wrappers ─────────────────────────────────────────────

    def log_case_created(self, case_number: str, performed_by: str, data: dict) -> None:
        self.log(case_number, "CASE_CREATED", performed_by, data)

    def log_case_status_changed(self, case_number: str, performed_by: str, from_status: str, to_status: str) -> None:
        self.log(case_number, "CASE_STATUS_CHANGED", performed_by, {"from": from_status, "to": to_status})

    def log_report_edited(self, case_number: str, performed_by: str, char_delta: Optional[int] = None) -> None:
        details = {"char_delta": char_delta} if char_delta is not None else {}
        self.log(case_number, "REPORT_EDITED", performed_by, details)

    def log_report_finalized(self, case_number: str, performed_by: str, pdf_hash: str) -> None:
        self.log(case_number, "REPORT_FINALIZED", performed_by, {"pdf_hash": pdf_hash})

    def log_evidence_added(self, case_number: str, performed_by: str, item_number: str) -> None:
        self.log(case_number, "EVIDENCE_ADDED", performed_by, {"item_number": item_number})

    def log_legal_process_added(self, case_number: str, performed_by: str, process_type: str) -> None:
        self.log(case_number, "LEGAL_PROCESS_ADDED", performed_by, {"process_type": process_type})

    def log_template_used(self, case_number: str, performed_by: str, template_name: str) -> None:
        self.log(case_number, "TEMPLATE_INSERTED", performed_by, {"template_name": template_name})

    def log_glossary_footnote(self, case_number: str, performed_by: str, term: str, footnote_num: int) -> None:
        self.log(case_number, "GLOSSARY_FOOTNOTE_ADDED", performed_by, {"term": term, "footnote_number": footnote_num})

    def log_note_event(
        self,
        case_number: str,
        performed_by: str,
        event_type: str,
        note_id: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Convenience wrapper for note lifecycle events."""
        details: Dict[str, Any] = {"note_id": note_id}
        if extra:
            details.update(extra)
        self.log(case_number, event_type, performed_by, details)

    def log_peer_review_event(
        self,
        case_number: str,
        performed_by: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Convenience wrapper for peer-review events."""
        self.log(case_number, f"PEER_REVIEW_{action.upper()}", performed_by, details or {})

    def log_event(
        self,
        event_type: str,
        description: str,
        actor: str,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generic event helper used by other services."""
        details: Dict[str, Any] = {"description": description}
        if entity_id:
            details["entity_id"] = entity_id
        if metadata:
            details.update(metadata)
        case_number = (metadata or {}).get("case_number", "")
        self.log(str(case_number), event_type, actor, details)
