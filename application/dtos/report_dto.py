"""application/dtos/report_dto.py — Report data transfer objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ReportDto:
    """Read model returned from IReportService."""

    report_id: int
    case_number: str
    status: str
    created_by: str
    created_at: datetime
    modified_at: Optional[datetime]
    modified_by: Optional[str]
    finalized_by: Optional[str]
    finalized_at: Optional[datetime]
    final_pdf_hash: Optional[str]
    word_count: int = 0
    appendix_count: int = 0


@dataclass
class CreateReportDto:
    """Input model for creating a new report."""

    case_number: str
    created_by: str
    template_id: Optional[int] = None
    initial_html: Optional[str] = None
