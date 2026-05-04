"""application/services/peer_review_service.py — PeerReviewService (Phase 6)."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from application.interfaces.i_audit_service import IAuditService
from application.interfaces.i_clock import IClock
from application.interfaces.i_peer_review_service import IPeerReviewService
from application.interfaces.i_report_repository import IReportRepository
from application.services._clock import DefaultClock
from domain.exceptions.domain_exceptions import DomainValidationError


class PeerReviewService(IPeerReviewService):
    """Application service managing peer review workflow for forensic reports."""

    def __init__(
        self,
        report_repository: IReportRepository,
        audit_service: IAuditService,
        clock: Optional[IClock] = None,
    ) -> None:
        self._reports = report_repository
        self._audit = audit_service
        self._clock = clock or DefaultClock()
        # In-memory stores — keys are report_id (int)
        self._comments: Dict[int, List[dict]] = {}
        self._sign_offs: Dict[int, List[dict]] = {}

    # ------------------------------------------------------------------ #
    # Export / Import                                                      #
    # ------------------------------------------------------------------ #

    def export_report_for_review(self, report_id: int, exported_by: str, output_path: str) -> str:
        report = self._reports.get_by_id(str(report_id))
        if report is None:
            raise DomainValidationError("report_id", f"Report '{report_id}' not found.")
        package = {
            "report_id": report_id,
            "title": f"Report {report_id}",
            "html_content": report.report_html or "",
            "exported_by": exported_by,
            "exported_at": self._clock.utcnow().isoformat(),
            "comments": self._comments.get(report_id, []),
        }
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(package, fh, indent=2, default=str)
        self._audit.log_event(
            event_type="REPORT_EXPORTED_FOR_REVIEW",
            description=f"Report {report_id} exported for peer review to '{output_path}'",
            actor=exported_by,
            entity_id=str(report_id),
            metadata={"output_path": output_path},
        )
        return output_path

    def import_reviewed_report(self, report_id: int, import_path: str, imported_by: str) -> dict:
        if not os.path.isfile(import_path):
            raise DomainValidationError("import_path", f"File '{import_path}' does not exist.")
        with open(import_path, "r", encoding="utf-8") as fh:
            package: dict = json.load(fh)
        # Merge comments from the reviewed package
        incoming_comments: List[dict] = package.get("comments", [])
        existing = self._comments.setdefault(report_id, [])
        existing_refs = {(c["location_ref"], c["commented_by"]) for c in existing}
        for comment in incoming_comments:
            key = (comment.get("location_ref"), comment.get("commented_by"))
            if key not in existing_refs:
                existing.append(comment)
                existing_refs.add(key)
        self._audit.log_event(
            event_type="REVIEWED_REPORT_IMPORTED",
            description=f"Peer-reviewed package imported for report {report_id}",
            actor=imported_by,
            entity_id=str(report_id),
            metadata={"import_path": import_path, "new_comments": len(incoming_comments)},
        )
        return {
            "report_id": report_id,
            "imported_comments": len(incoming_comments),
            "import_path": import_path,
        }

    # ------------------------------------------------------------------ #
    # Comments                                                             #
    # ------------------------------------------------------------------ #

    def add_comment(self, report_id: int, location_ref: str, comment: str, commented_by: str) -> None:
        if not comment or not comment.strip():
            raise DomainValidationError("comment", "Comment text cannot be empty.")
        self._comments.setdefault(report_id, []).append(
            {
                "location_ref": location_ref,
                "comment": comment.strip(),
                "commented_by": commented_by,
                "commented_at": self._clock.utcnow().isoformat(),
            }
        )
        self._audit.log_event(
            event_type="PEER_REVIEW_COMMENT_ADDED",
            description=f"Comment added at '{location_ref}' on report {report_id}",
            actor=commented_by,
            entity_id=str(report_id),
        )

    def get_comments(self, report_id: int) -> List[dict]:
        return list(self._comments.get(report_id, []))

    # ------------------------------------------------------------------ #
    # Sign-offs                                                            #
    # ------------------------------------------------------------------ #

    def mark_sign_off(
        self, report_id: int, reviewer_username: str, approved: bool, notes: str = ""
    ) -> None:
        self._sign_offs.setdefault(report_id, []).append(
            {
                "reviewer": reviewer_username,
                "approved": approved,
                "notes": notes,
                "signed_off_at": self._clock.utcnow().isoformat(),
            }
        )
        decision = "APPROVED" if approved else "REJECTED"
        self._audit.log_event(
            event_type=f"PEER_REVIEW_{decision}",
            description=f"Report {report_id} {decision.lower()} by '{reviewer_username}'",
            actor=reviewer_username,
            entity_id=str(report_id),
            metadata={"notes": notes},
        )

    def get_review_summary(self, report_id: int) -> dict:
        comments = self._comments.get(report_id, [])
        sign_offs = self._sign_offs.get(report_id, [])
        approved_count = sum(1 for s in sign_offs if s["approved"])
        rejected_count = len(sign_offs) - approved_count
        overall_status: str
        if not sign_offs:
            overall_status = "PENDING"
        elif rejected_count > 0:
            overall_status = "REJECTED"
        elif approved_count > 0:
            overall_status = "APPROVED"
        else:
            overall_status = "PENDING"
        return {
            "report_id": report_id,
            "total_comments": len(comments),
            "sign_offs": len(sign_offs),
            "approved": approved_count,
            "rejected": rejected_count,
            "overall_status": overall_status,
        }
