"""
infrastructure/middleware/request_logger.py

Flask middleware that logs every inbound HTTP request and its response as a
structured JSON log entry via :mod:`infrastructure.observability`.

The middleware also optionally writes a lightweight audit record for
write-mutating endpoints (POST, PUT, PATCH, DELETE) via the standard
application AuditService.  This gives a centralised HTTP audit trail that
complements the domain-level audit entries.

Usage
-----
Register once at application startup:

    from infrastructure.middleware.request_logger import register_request_logging
    register_request_logging(app)

For audit trail integration, pass an ``AuditService`` instance:

    register_request_logging(app, audit_service=audit_svc)

Every request then appears in the structured log like:

    {
        "timestamp": "2026-04-23T12:01:00.000000+00:00",
        "level":     "INFO",
        "logger":    "http.access",
        "request_id": "f3c2...",
        "message":   "POST /api/v1/cases 201",
        "method":    "POST",
        "path":      "/api/v1/cases",
        "status":    201,
        "latency_ms": 42.1,
        "user":      "alice",
        "ip":        "127.0.0.1"
    }
"""

from __future__ import annotations

import time
from typing import Optional

from flask import Flask, g, request

from infrastructure.observability.structured_logger import (
    bind_request_id,
    get_logger,
)

_access_log = get_logger("http.access")

# Write-mutating HTTP verbs that should be recorded in the audit trail
_AUDIT_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Endpoints excluded from audit logging (e.g. health checks, metrics)
_AUDIT_EXCLUDE_PATHS = frozenset({"/metrics", "/health", "/healthz"})


def _safe_user() -> str:
    """Best-effort extraction of the JWT identity without raising."""
    try:
        from flask_jwt_extended import get_jwt_identity

        ident = get_jwt_identity()
        if isinstance(ident, dict):
            return str(ident.get("username", "anonymous"))
        return str(ident) if ident else "anonymous"
    except Exception:
        return "anonymous"


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def register_request_logging(
    app: Flask,
    audit_service=None,
    log_request_body: bool = False,
) -> None:
    """Wire request/response logging into *app*.

    Parameters
    ----------
    app:
        Flask application instance.
    audit_service:
        Optional :class:`application.services.audit_service.AuditService`
        instance.  When provided, mutating requests are recorded in the
        domain audit chain under the event type ``HTTP_REQUEST``.
    log_request_body:
        If ``True``, include the parsed JSON request body in the log entry.
        Disabled by default to avoid logging sensitive payloads.
    """

    @app.before_request
    def _log_before_request() -> None:
        # Bind (or inherit) request ID — server.py may already have done this,
        # so we only set one if the context variable is still empty.
        from infrastructure.observability.structured_logger import current_request_id

        if not current_request_id():
            rid = request.headers.get("X-Request-ID") or None
            bind_request_id(rid)

        g._req_start = time.perf_counter()
        g._req_user = "anonymous"  # resolved after auth in after_request

    @app.after_request
    def _log_after_request(response):
        latency_ms = (
            time.perf_counter() - getattr(g, "_req_start", time.perf_counter())
        ) * 1000

        user = _safe_user()
        ip = _client_ip()

        extra: dict = {
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "latency_ms": round(latency_ms, 2),
            "user": user,
            "ip": ip,
        }

        if log_request_body and request.is_json:
            try:
                body = request.get_json(silent=True, cache=True)
                if body is not None:
                    extra["request_body"] = body
            except Exception:
                pass

        msg = f"{request.method} {request.path} {response.status_code}"
        _access_log.info(msg, extra=extra)

        # Domain audit trail — only for mutating verbs on non-excluded paths
        if (
            audit_service is not None
            and request.method in _AUDIT_METHODS
            and request.path not in _AUDIT_EXCLUDE_PATHS
        ):
            try:
                audit_service.log(
                    case_number="_system",
                    event_type="HTTP_REQUEST",
                    performed_by=user,
                    details={
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "ip": ip,
                    },
                )
            except Exception:
                # Never let audit failures disrupt the response
                _access_log.warning(
                    "Audit trail write failed for HTTP request",
                    extra={"path": request.path},
                )

        return response
