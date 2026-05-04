"""application/dtos/audit_dto.py - Audit DTOs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class AuditEntryDto:
    entry_id: str
    case_number: str
    event_type: str
    performed_by: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    entry_hash: str = ""
