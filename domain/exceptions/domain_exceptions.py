"""
domain/exceptions — Strongly-typed domain-level exceptions.

These replace generic ValueError / AssertionError calls
and allow callers to handle specific failure modes.
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for all domain exceptions."""


# ── Validation ─────────────────────────────────────────────────────────────

class DomainValidationError(DomainError):
    """Raised when an entity value fails a domain rule."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"Validation error on '{field}': {message}")


# ── Status transitions ──────────────────────────────────────────────────────

class InvalidStatusTransitionError(DomainError):
    """Raised when a requested status transition violates the state machine."""

    def __init__(self, entity_id: str, from_status: str, to_status: str) -> None:
        self.entity_id = entity_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Cannot transition '{entity_id}' from '{from_status}' to '{to_status}'."
        )


# ── Entity lookup ───────────────────────────────────────────────────────────

class EntityNotFoundError(DomainError):
    """Raised when an expected entity does not exist."""

    def __init__(self, entity_type: str, identifier: Any) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} with identifier '{identifier}' was not found.")


# ── Duplicates ──────────────────────────────────────────────────────────────

class DuplicateEntityError(DomainError):
    """Raised when an entity already exists and duplicates are not allowed."""

    def __init__(self, entity_type: str, identifier: Any) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} '{identifier}' already exists.")


# ── Archive / immutability guards ───────────────────────────────────────────

class CaseArchivedError(DomainError):
    """Raised when a mutating operation is attempted on an archived case."""

    def __init__(self, case_number: str) -> None:
        self.case_number = case_number
        super().__init__(f"Case '{case_number}' is archived and cannot be modified.")


class ReportFinalizedError(DomainError):
    """Raised when a write is attempted on a finalized / archived report."""

    def __init__(self, report_id: int) -> None:
        self.report_id = report_id
        super().__init__(f"Report {report_id} is finalized and cannot be edited.")


# ── Typed status-transition exceptions ────────────────────────────────────

class InvalidCaseStatusTransitionError(InvalidStatusTransitionError):
    """Typed variant carrying CaseStatus enum values for case transitions."""

    def __init__(self, case_number: str, from_status, to_status) -> None:
        self.case_number = case_number
        self.current_status = from_status
        self.target_status = to_status
        super().__init__(case_number, str(from_status), str(to_status))


class InvalidEvidenceStatusError(DomainError):
    """Raised when an evidence status transition violates the state machine."""

    def __init__(self, evidence_id, from_status, to_status) -> None:
        self.evidence_id = evidence_id
        self.current_status = from_status
        self.target_status = to_status
        super().__init__(
            f"Evidence '{evidence_id}' cannot transition from '{from_status}' to '{to_status}'."
        )


class InvalidLegalProcessStatusError(DomainError):
    """Raised when a legal-process status transition violates the state machine."""

    def __init__(self, process_id, from_status, to_status) -> None:
        self.process_id = process_id
        self.current_status = from_status
        self.target_status = to_status
        super().__init__(
            f"Legal process '{process_id}' cannot transition from '{from_status}' to '{to_status}'."
        )


# ── Access control ─────────────────────────────────────────────────────────

class UnauthorizedOperationError(DomainError):
    """Raised when a user's role does not permit the requested operation."""

    def __init__(
        self,
        username: str,
        operation: str,
        required_role: str = "Investigator",
    ) -> None:
        self.username = username
        self.operation = operation
        self.required_role = required_role
        super().__init__(
            f"User '{username}' is not authorised to perform '{operation}'. "
            f"Required role: {required_role}."
        )


# ── Entity-level field validation ──────────────────────────────────────────

class InvalidEntityError(DomainError):
    """Raised when an entity field violates a domain invariant during construction.

    Carries structured context (entity name, field name, and reason) for
    programmatic error handling — distinct from :class:`DomainValidationError`
    which is used for service-layer DTO validation.
    """

    def __init__(self, entity_name: str, field_name: str, reason: str) -> None:
        self.entity_name = entity_name
        self.field_name = field_name
        self.reason = reason
        super().__init__(
            f"Invalid field '{field_name}' on entity '{entity_name}': {reason}"
        )


# ── Audit chain ─────────────────────────────────────────────────────────────

class AuditChainCorruptedError(DomainError):
    """Raised when the SHA-256 hash chain of audit entries fails verification."""

    def __init__(self, entry_index: int) -> None:
        self.entry_index = entry_index
        super().__init__(
            f"Audit chain integrity failure detected at entry index {entry_index}."
        )


# ── Template ────────────────────────────────────────────────────────────────

class TemplatePlaceholderError(DomainError):
    """Raised when required template placeholders are missing or invalid."""

    def __init__(self, placeholder: str, reason: str) -> None:
        self.placeholder = placeholder
        self.reason = reason
        super().__init__(f"Placeholder '{placeholder}': {reason}")


__all__ = [
    "DomainError",
    "DomainValidationError",
    "InvalidStatusTransitionError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "CaseArchivedError",
    "ReportFinalizedError",
    "AuditChainCorruptedError",
    "TemplatePlaceholderError",
]
