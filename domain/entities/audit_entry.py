"""domain/entities/audit_entry.py — SHA-256 hash-chained tamper-evident audit entry."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class AuditEntry:
    """
    Single entry in the tamper-evident audit chain.

    Each entry records a hash of its own content and the hash of the
    previous entry, forming a chain that makes undetected modification
    of any historical entry impossible.
    """

    # ── Identity ─────────────────────────────────────────────────────────
    id: Optional[int]            # None until persisted
    case_number: str
    event_type: str              # e.g. "CASE_CREATED", "REPORT_EDITED"
    performed_by: str

    # ── Payload ──────────────────────────────────────────────────────────
    details: Dict[str, Any] = field(default_factory=dict)

    # ── Timestamps ───────────────────────────────────────────────────────
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # ── Hash chain ───────────────────────────────────────────────────────
    previous_hash: str = field(default="0" * 64)
    entry_hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    # ================================================================== #
    # Factory                                                              #
    # ================================================================== #

    @classmethod
    def create(
        cls,
        case_number: str,
        event_type: str,
        performed_by: str,
        details: Optional[Dict[str, Any]] = None,
        previous_hash: str = "0" * 64,
    ) -> "AuditEntry":
        entry = cls(
            id=None,
            case_number=case_number,
            event_type=event_type,
            performed_by=performed_by,
            details=details or {},
            previous_hash=previous_hash,
        )
        return entry

    # ================================================================== #
    # Hashing                                                              #
    # ================================================================== #

    def _compute_hash(self) -> str:
        payload = {
            "timestamp": self.timestamp.isoformat(),
            "case_number": self.case_number,
            "event_type": self.event_type,
            "performed_by": self.performed_by,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }
        serialised = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    def recompute_hash(self) -> None:
        """Recompute and store entry_hash (call after setting previous_hash)."""
        self.entry_hash = self._compute_hash()

    def verify_integrity(self) -> bool:
        """Return True if entry_hash matches the recomputed hash."""
        return self.entry_hash == self._compute_hash()

    # ================================================================== #
    # Properties                                                           #
    # ================================================================== #

    @property
    def entity_id(self) -> str:
        return str(self.id) if self.id is not None else ""

    def __repr__(self) -> str:
        return (
            f"AuditEntry(id={self.id}, event={self.event_type!r}, "
            f"case={self.case_number!r}, by={self.performed_by!r})"
        )
