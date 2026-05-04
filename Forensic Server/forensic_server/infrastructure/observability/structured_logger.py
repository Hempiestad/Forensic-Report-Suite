from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional


_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def bind_request_id(request_id: Optional[str] = None) -> str:
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def current_request_id() -> str:
    return _request_id_var.get()


_SKIP_ATTRS = frozenset(
    {
        "args", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module", "msecs",
        "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "taskName", "thread", "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="microseconds")
        doc = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "request_id": current_request_id(),
            "message": record.message,
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP_ATTRS and not key.startswith("_"):
                doc[key] = value
        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            doc["exception"] = record.exc_text
        if record.stack_info:
            doc["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(doc, default=str)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        return True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(level: int = logging.INFO, output_file: Optional[str] = None, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 10) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    formatter = JsonFormatter()
    request_filter = RequestIdFilter()

    def _has_exact_handler(cls: type) -> bool:
        return any(type(handler) is cls for handler in root.handlers)

    if not _has_exact_handler(logging.StreamHandler):
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(request_filter)
        root.addHandler(stream_handler)

    if output_file and not _has_exact_handler(RotatingFileHandler):
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        file_handler = RotatingFileHandler(output_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_filter)
        root.addHandler(file_handler)
