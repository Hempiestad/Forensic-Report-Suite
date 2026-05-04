"""domain/enums/audit_event_type.py — Typed audit event name constants.

Using a class of string constants (rather than Enum) keeps JSON serialisation
simple — values are already plain strings and require no .value access.
All consumers should import from here rather than using raw string literals,
to prevent typos and ensure consistent audit trail naming.
"""
from __future__ import annotations


class AuditEventType:
    """Namespace of all well-known audit event type strings."""

    # ── Case ────────────────────────────────────────────────────────────
    CASE_CREATED = "CASE_CREATED"
    CASE_UPDATED = "CASE_UPDATED"
    CASE_DELETED = "CASE_DELETED"
    CASE_ARCHIVED = "CASE_ARCHIVED"
    CASE_RESTORED = "CASE_RESTORED"
    CASE_STATUS_CHANGED = "CASE_STATUS_CHANGED"
    CASE_SUBMITTED = "CASE_SUBMITTED"
    CASE_APPROVED = "CASE_APPROVED"
    CASE_REVISIONS_REQUESTED = "CASE_REVISIONS_REQUESTED"
    CASE_COMPLETED = "CASE_COMPLETED"
    CASE_CLOSED = "CASE_CLOSED"
    CASE_PDF_HASH_SET = "CASE_PDF_HASH_SET"
    CASE_ENCRYPTED_METADATA_SET = "CASE_ENCRYPTED_METADATA_SET"
    CASE_ENCRYPTED_REPORT_SET = "CASE_ENCRYPTED_REPORT_SET"
    CASE_LEGAL_COUNTS_UPDATED = "CASE_LEGAL_COUNTS_UPDATED"

    # ── Evidence ────────────────────────────────────────────────────────
    EVIDENCE_CREATED = "EVIDENCE_CREATED"
    EVIDENCE_UPDATED = "EVIDENCE_UPDATED"
    EVIDENCE_DELETED = "EVIDENCE_DELETED"
    EVIDENCE_IMAGED = "EVIDENCE_IMAGED"
    EVIDENCE_IMAGING_STARTED = "EVIDENCE_IMAGING_STARTED"
    EVIDENCE_IMAGING_STATUS_UPDATED = "EVIDENCE_IMAGING_STATUS_UPDATED"

    # ── Note ────────────────────────────────────────────────────────────
    NOTE_CREATED = "NOTE_CREATED"
    NOTE_UPDATED = "NOTE_UPDATED"
    NOTE_DELETED = "NOTE_DELETED"
    NOTE_ARCHIVED = "NOTE_ARCHIVED"
    NOTE_RESTORED = "NOTE_RESTORED"
    NOTE_SUBMITTED_FOR_APPROVAL = "NOTE_SUBMITTED_FOR_APPROVAL"
    NOTE_APPROVED = "NOTE_APPROVED"
    NOTE_REJECTED = "NOTE_REJECTED"
    NOTE_REDACTED = "NOTE_REDACTED"
    NOTE_UNREDACTED = "NOTE_UNREDACTED"
    NOTE_TAG_ADDED = "NOTE_TAG_ADDED"
    NOTE_TAG_REMOVED = "NOTE_TAG_REMOVED"
    NOTE_SHARED = "NOTE_SHARED"
    NOTE_UNSHARED = "NOTE_UNSHARED"
    NOTE_VISIBILITY_CHANGED = "NOTE_VISIBILITY_CHANGED"
    NOTE_ATTACHMENT_ADDED = "NOTE_ATTACHMENT_ADDED"
    NOTE_ATTACHMENT_REMOVED = "NOTE_ATTACHMENT_REMOVED"
    NOTE_EXPORTED = "NOTE_EXPORTED"

    # ── Task (note sub-type) ─────────────────────────────────────────────
    TASK_CREATED = "TASK_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_REOPENED = "TASK_REOPENED"
    TASK_REASSIGNED = "TASK_REASSIGNED"

    # ── Legal process ────────────────────────────────────────────────────
    LEGAL_PROCESS_CREATED = "LEGAL_PROCESS_CREATED"
    LEGAL_PROCESS_UPDATED = "LEGAL_PROCESS_UPDATED"
    LEGAL_PROCESS_DELETED = "LEGAL_PROCESS_DELETED"
    LEGAL_PROCESS_SUBMITTED = "LEGAL_PROCESS_SUBMITTED"
    LEGAL_PROCESS_RECEIVED = "LEGAL_PROCESS_RECEIVED"
    LEGAL_PROCESS_COMPLETED = "LEGAL_PROCESS_COMPLETED"
    LEGAL_PROCESS_CANCELLED = "LEGAL_PROCESS_CANCELLED"
    LEGAL_PROCESS_EXPIRED = "LEGAL_PROCESS_EXPIRED"
    LEGAL_PROCESS_APPROVED_INVESTIGATOR = "LEGAL_PROCESS_APPROVED_INVESTIGATOR"
    LEGAL_PROCESS_APPROVED_STATE_ATTORNEY = "LEGAL_PROCESS_APPROVED_STATE_ATTORNEY"
    LEGAL_PROCESS_APPROVED_JUDICIAL = "LEGAL_PROCESS_APPROVED_JUDICIAL"

    # ── Court date ───────────────────────────────────────────────────────
    COURT_DATE_ADDED = "COURT_DATE_ADDED"
    COURT_DATE_UPDATED = "COURT_DATE_UPDATED"
    COURT_DATE_REMOVED = "COURT_DATE_REMOVED"

    # ── Investigative lead ───────────────────────────────────────────────
    LEAD_CREATED = "LEAD_CREATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    LEAD_DELETED = "LEAD_DELETED"
    LEAD_STATUS_CHANGED = "LEAD_STATUS_CHANGED"

    # ── Report ───────────────────────────────────────────────────────────
    REPORT_CREATED = "REPORT_CREATED"
    REPORT_UPDATED = "REPORT_UPDATED"
    REPORT_DELETED = "REPORT_DELETED"
    REPORT_FINALIZED = "REPORT_FINALIZED"
    REPORT_EXPORTED = "REPORT_EXPORTED"

    # ── Template ─────────────────────────────────────────────────────────
    TEMPLATE_CREATED = "TEMPLATE_CREATED"
    TEMPLATE_UPDATED = "TEMPLATE_UPDATED"
    TEMPLATE_DELETED = "TEMPLATE_DELETED"
    TEMPLATE_PUBLISHED = "TEMPLATE_PUBLISHED"
    TEMPLATE_CLONED = "TEMPLATE_CLONED"
    TEMPLATE_EXPORTED = "TEMPLATE_EXPORTED"
    TEMPLATE_IMPORTED = "TEMPLATE_IMPORTED"

    # ── Peer review ──────────────────────────────────────────────────────
    PEER_REVIEW_REQUESTED = "PEER_REVIEW_REQUESTED"
    PEER_REVIEW_SUBMITTED = "PEER_REVIEW_SUBMITTED"
    PEER_REVIEW_APPROVED = "PEER_REVIEW_APPROVED"
    PEER_REVIEW_REJECTED = "PEER_REVIEW_REJECTED"

    # ── User / security ──────────────────────────────────────────────────
    USER_LOGIN = "USER_LOGIN"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    USER_LOGOUT = "USER_LOGOUT"
    USER_LOCKED_OUT = "USER_LOCKED_OUT"
    USER_PASSWORD_CHANGED = "USER_PASSWORD_CHANGED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    USER_CREATED = "USER_CREATED"
    USER_DELETED = "USER_DELETED"

    # ── System ───────────────────────────────────────────────────────────
    SYSTEM_MIGRATION = "SYSTEM_MIGRATION"
    SYSTEM_BACKUP = "SYSTEM_BACKUP"
    SYSTEM_RESTORE = "SYSTEM_RESTORE"
    SYSTEM_ERROR = "SYSTEM_ERROR"

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def all_values(cls) -> list[str]:
        """Return every defined event type string."""
        return [
            v for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str)
        ]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Return True if *value* is a known event type."""
        return value in cls.all_values()
