"""
infrastructure/observability/structured_logger.py

Structured JSON logging with per-request ID propagation.

Usage
-----
    from infrastructure.observability import configure_logging, get_logger, bind_request_id

    # Bootstrap once at application startup:
    configure_logging(level=logging.INFO, output_file="logs/app.log")

    # In Flask before_request (or any entry-point):
    bind_request_id()          # generates a new UUID and stores it in context

    # In any module:
    logger = get_logger(__name__)
    logger.info("case created", extra={"case_id": "C-001", "user": "alice"})

Every log record emitted through these loggers will be a single JSON line:
    {
        "timestamp": "2026-04-23T12:00:00.123456Z",
        "level": "INFO",
        "logger": "cases_bp",
        "request_id": "f3c2...",
        "message": "case created",
        "case_id": "C-001",
        "user": "alice"
    }
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional

# ---------------------------------------------------------------------------
# Request-ID context variable (works with both threading and asyncio)
# ---------------------------------------------------------------------------

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def bind_request_id(request_id: Optional[str] = None) -> str:
    """Set a request ID in the current context.

    If *request_id* is None a new UUID4 is generated.  Returns the ID that
    was stored so callers can forward it to downstream services.
    """
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def current_request_id() -> str:
    """Return the request ID bound to the current context, or an empty string."""
    return _request_id_var.get()


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------

# Keys that are present on every LogRecord but are not interesting as
# structured fields — we skip them to keep the JSON compact.
_SKIP_ATTRS = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """Formats log records as newline-delimited JSON.

    Core fields
    -----------
    - ``timestamp``  ISO-8601 UTC (microsecond precision)
    - ``level``      uppercased level name
    - ``logger``     logger name (``record.name``)
    - ``request_id`` current request ID from context (empty string if unset)
    - ``message``    fully formatted message string

    Any key/value pairs added via ``extra={}`` are merged at the top level.
    Exception tracebacks are added under ``exception`` when present.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Ensure record.message is populated
        record.message = record.getMessage()

        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
            timespec="microseconds"
        )

        doc: dict = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "request_id": current_request_id(),
            "message": record.message,
        }

        # Merge any caller-supplied extra fields
        for key, value in record.__dict__.items():
            if key not in _SKIP_ATTRS and not key.startswith("_"):
                doc[key] = value

        # Exception info
        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            doc["exception"] = record.exc_text

        # Stack info
        if record.stack_info:
            doc["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(doc, default=str)


# ---------------------------------------------------------------------------
# Filter that injects request_id into every record (belt-and-suspenders)
# ---------------------------------------------------------------------------


class RequestIdFilter(logging.Filter):
    """Adds ``request_id`` attribute to every log record.

    Because JsonFormatter reads ``request_id`` from the context variable
    directly, this filter is optional but useful when using non-JSON
    formatters in the same handler chain.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()  # type: ignore[attr-defined]
        return True


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return the named logger.

    Note: the formatter is applied to handlers, not loggers, so the returned
    logger will produce JSON only after :func:`configure_logging` has been
    called, or if a ``JsonFormatter`` handler has been added manually.
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# One-call logging bootstrap
# ---------------------------------------------------------------------------


def configure_logging(
    level: int = logging.INFO,
    output_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 10,
) -> None:
    """Configure the root logger with JSON output.

    Parameters
    ----------
    level:
        Logging level (e.g. ``logging.DEBUG``, ``logging.INFO``).
    output_file:
        Optional path to a rotating log file.  If *None*, logs go to
        *stderr* only.
    max_bytes:
        Maximum size of each log file before rotation (default 10 MB).
    backup_count:
        Number of rotated log files to retain (default 10).

    Idempotent — calling it multiple times with the same arguments is safe;
    duplicate handlers are not added.
    """
    root = logging.getLogger()
    root.setLevel(level)

    formatter = JsonFormatter()
    request_filter = RequestIdFilter()

    def _has_handler(cls: type) -> bool:
        return any(isinstance(h, cls) for h in root.handlers)

    # Always ensure a stderr stream handler
    if not _has_handler(logging.StreamHandler):
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(request_filter)
        root.addHandler(stream_handler)

    # Optional rotating file handler
    if output_file and not _has_handler(RotatingFileHandler):
        import os
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        file_handler = RotatingFileHandler(
            output_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_filter)
        root.addHandler(file_handler)
