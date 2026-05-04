"""
infrastructure/logging/ — Structured logging and audit chain wiring (Phase 3).

AuditService implementation connects domain AuditEntry hashing with the
SQLite persistence layer to replace the legacy file-based audit_log.py.
"""
