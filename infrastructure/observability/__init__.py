"""
infrastructure/observability/ — Structured JSON logging and metrics collection.

Provides:
- JsonFormatter: formats log records as newline-delimited JSON
- RequestIdFilter: injects a per-request UUID into every log record
- get_logger(name): factory returning a logger that uses the JSON formatter
- configure_logging(level, output_file): one-call bootstrap for the root logger
- MetricsCollector: thread-safe in-process counters, histograms, and gauges
"""

from infrastructure.observability.structured_logger import (
    JsonFormatter,
    RequestIdFilter,
    get_logger,
    configure_logging,
    bind_request_id,
    current_request_id,
)
from infrastructure.observability.metrics_collector import MetricsCollector, get_metrics
from infrastructure.observability.prometheus_exporter import generate_prometheus_text

__all__ = [
    "JsonFormatter",
    "RequestIdFilter",
    "get_logger",
    "configure_logging",
    "bind_request_id",
    "current_request_id",
    "MetricsCollector",
    "get_metrics",
    "generate_prometheus_text",
]
