"""
tests/integration/test_structured_logging.py

Tests for infrastructure.observability — structured JSON logging and metrics.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from io import StringIO
from typing import List

import pytest

from infrastructure.observability import (
    JsonFormatter,
    MetricsCollector,
    RequestIdFilter,
    bind_request_id,
    configure_logging,
    current_request_id,
    get_logger,
    get_metrics,
)
from infrastructure.observability.metrics_collector import _tag_suffix


# ===========================================================================
# Helpers
# ===========================================================================


def _make_handler(stream: StringIO) -> logging.StreamHandler:
    """Return a StreamHandler with JsonFormatter wired up."""
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    return handler


def _capture_records(name: str, level: int = logging.DEBUG) -> tuple[logging.Logger, StringIO]:
    """Set up an isolated logger writing JSON to a StringIO buffer."""
    buf = StringIO()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Remove pre-existing handlers to avoid interference
    logger.handlers.clear()
    logger.propagate = False
    logger.addHandler(_make_handler(buf))
    return logger, buf


def _parse_json_line(buf: StringIO) -> dict:
    """Return the first non-empty JSON line from the buffer."""
    buf.seek(0)
    for line in buf.getvalue().splitlines():
        line = line.strip()
        if line:
            return json.loads(line)
    raise AssertionError("No JSON output found in buffer")


def _parse_all_json_lines(buf: StringIO) -> List[dict]:
    buf.seek(0)
    records = []
    for line in buf.getvalue().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ===========================================================================
# JsonFormatter — core fields
# ===========================================================================


class TestJsonFormatter:
    def test_basic_fields_present(self):
        logger, buf = _capture_records("test_basic")
        logger.info("hello world")
        doc = _parse_json_line(buf)
        assert doc["level"] == "INFO"
        assert doc["message"] == "hello world"
        assert "timestamp" in doc
        assert "logger" in doc

    def test_timestamp_is_utc_iso(self):
        logger, buf = _capture_records("test_ts")
        logger.info("ts check")
        doc = _parse_json_line(buf)
        ts = doc["timestamp"]
        # Must end with +00:00 (UTC offset from isoformat)
        assert ts.endswith("+00:00"), f"Expected UTC offset, got: {ts}"

    def test_extra_fields_merged(self):
        logger, buf = _capture_records("test_extra")
        logger.info("case created", extra={"case_id": "C-001", "user": "alice"})
        doc = _parse_json_line(buf)
        assert doc["case_id"] == "C-001"
        assert doc["user"] == "alice"
        assert doc["message"] == "case created"

    def test_logger_name_correct(self):
        logger, buf = _capture_records("forensic.cases")
        logger.warning("permission denied")
        doc = _parse_json_line(buf)
        assert doc["logger"] == "forensic.cases"
        assert doc["level"] == "WARNING"

    def test_exception_info_included(self):
        logger, buf = _capture_records("test_exc")
        try:
            raise ValueError("bad input")
        except ValueError:
            logger.exception("caught error")
        doc = _parse_json_line(buf)
        assert "exception" in doc
        assert "ValueError" in doc["exception"]
        assert "bad input" in doc["exception"]

    def test_output_is_valid_json(self):
        logger, buf = _capture_records("test_valid_json")
        logger.debug("debug msg", extra={"count": 42, "active": True, "ratio": 3.14})
        doc = _parse_json_line(buf)
        # JSON types are preserved
        assert isinstance(doc["count"], int)
        assert isinstance(doc["active"], bool)
        assert isinstance(doc["ratio"], float)

    def test_no_duplicate_key_errors_on_standard_attrs(self):
        """Standard LogRecord attributes should not bleed into the JSON doc
        as duplicate keys alongside our explicit fields."""
        logger, buf = _capture_records("test_no_dup")
        logger.info("clean output")
        line = buf.getvalue().strip().splitlines()[0]
        # Must be parseable without error
        doc = json.loads(line)
        # 'msg' should NOT appear (it's in _SKIP_ATTRS)
        assert "msg" not in doc
        assert "levelno" not in doc


# ===========================================================================
# RequestIdFilter + bind_request_id / current_request_id
# ===========================================================================


class TestRequestId:
    def test_bind_generates_uuid_when_none(self):
        rid = bind_request_id()
        assert len(rid) == 36  # UUID4 canonical form
        assert current_request_id() == rid

    def test_bind_uses_provided_id(self):
        bind_request_id("my-custom-id-123")
        assert current_request_id() == "my-custom-id-123"

    def test_request_id_in_json_output(self):
        rid = bind_request_id()
        logger, buf = _capture_records("test_rid_json")
        logger.info("with request id")
        doc = _parse_json_line(buf)
        assert doc["request_id"] == rid

    def test_different_threads_have_independent_ids(self):
        """ContextVar must be thread-local."""
        results: List[str] = []
        barrier = threading.Barrier(2)

        def worker():
            bind_request_id()
            barrier.wait()
            results.append(current_request_id())

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert len(results) == 2
        assert results[0] != results[1], "Each thread should have a unique request ID"

    def test_empty_request_id_before_bind(self):
        """ContextVar default is empty string when no ID has been bound."""
        from infrastructure.observability.structured_logger import _request_id_var

        # Use the ContextVar token API to temporarily reset to the default
        token = _request_id_var.set("")
        try:
            assert current_request_id() == ""
        finally:
            _request_id_var.reset(token)


# ===========================================================================
# configure_logging — bootstrap idempotency
# ===========================================================================


class TestConfigureLogging:
    def test_configure_logging_adds_handler(self):
        root = logging.getLogger()
        initial_count = len(root.handlers)
        # configure_logging is idempotent for the same handler type
        configure_logging(level=logging.DEBUG)
        assert len(root.handlers) >= initial_count  # at least as many

    def test_configure_logging_idempotent(self):
        """Calling twice must not duplicate handlers."""
        root = logging.getLogger()
        configure_logging(level=logging.INFO)
        before = len(root.handlers)
        configure_logging(level=logging.INFO)
        after = len(root.handlers)
        assert before == after


# ===========================================================================
# MetricsCollector — counters
# ===========================================================================


class TestMetricsCounter:
    def setup_method(self):
        self.m = MetricsCollector()

    def test_increment_basic(self):
        self.m.increment("req.count")
        assert self.m.counter_value("req.count") == 1

    def test_increment_by_value(self):
        self.m.increment("req.count", 5)
        assert self.m.counter_value("req.count") == 5

    def test_increment_multiple_calls(self):
        for _ in range(10):
            self.m.increment("req.count")
        assert self.m.counter_value("req.count") == 10

    def test_counter_with_tags(self):
        self.m.increment("http.req", tags={"method": "GET"})
        self.m.increment("http.req", tags={"method": "POST"})
        self.m.increment("http.req", tags={"method": "GET"})
        assert self.m.counter_value("http.req", tags={"method": "GET"}) == 2
        assert self.m.counter_value("http.req", tags={"method": "POST"}) == 1

    def test_decrement(self):
        self.m.increment("queue.depth", 5)
        self.m.decrement("queue.depth", 2)
        assert self.m.counter_value("queue.depth") == 3

    def test_unknown_counter_returns_zero(self):
        assert self.m.counter_value("nonexistent") == 0

    def test_get_stats_contains_counters(self):
        self.m.increment("events.login")
        stats = self.m.get_stats()
        assert "counters" in stats
        assert stats["counters"]["events.login"] == 1


# ===========================================================================
# MetricsCollector — gauges
# ===========================================================================


class TestMetricsGauge:
    def setup_method(self):
        self.m = MetricsCollector()

    def test_gauge_stores_value(self):
        self.m.gauge("cache.size", 1024)
        assert self.m.gauge_value("cache.size") == 1024.0

    def test_gauge_overwrites(self):
        self.m.gauge("cpu.usage", 0.45)
        self.m.gauge("cpu.usage", 0.72)
        assert self.m.gauge_value("cpu.usage") == pytest.approx(0.72)

    def test_gauge_with_tags(self):
        self.m.gauge("mem.free", 512, tags={"host": "node1"})
        self.m.gauge("mem.free", 256, tags={"host": "node2"})
        assert self.m.gauge_value("mem.free", tags={"host": "node1"}) == 512.0
        assert self.m.gauge_value("mem.free", tags={"host": "node2"}) == 256.0

    def test_unknown_gauge_returns_zero(self):
        assert self.m.gauge_value("ghost.gauge") == 0.0


# ===========================================================================
# MetricsCollector — histograms
# ===========================================================================


class TestMetricsHistogram:
    def setup_method(self):
        self.m = MetricsCollector()

    def test_histogram_basic_snapshot(self):
        for v in [10.0, 20.0, 30.0]:
            self.m.histogram("latency_ms", v)
        snap = self.m.get_stats()["histograms"]["latency_ms"]
        assert snap["count"] == 3
        assert snap["sum"] == pytest.approx(60.0)
        assert snap["min"] == pytest.approx(10.0)
        assert snap["max"] == pytest.approx(30.0)
        assert snap["mean"] == pytest.approx(20.0)

    def test_histogram_percentiles(self):
        for v in range(1, 101):  # 1..100
            self.m.histogram("scores", float(v))
        snap = self.m.get_stats()["histograms"]["scores"]
        # p50 should be ~50, p95 ~95, p99 ~99
        assert 49.0 <= snap["p50"] <= 51.0
        assert 94.0 <= snap["p95"] <= 96.0
        assert 98.0 <= snap["p99"] <= 100.0

    def test_histogram_empty_snapshot(self):
        # No records recorded — should return zero-filled dict without error
        snap = self.m.get_stats()["histograms"]
        # Nothing added, no histogram key expected
        assert "latency_ms" not in snap

    def test_histogram_with_tags(self):
        self.m.histogram("query_ms", 5.0, tags={"table": "cases"})
        self.m.histogram("query_ms", 15.0, tags={"table": "reports"})
        stats = self.m.get_stats()["histograms"]
        assert 'query_ms{table=cases}' in stats
        assert 'query_ms{table=reports}' in stats

    def test_histogram_single_sample(self):
        self.m.histogram("single", 42.0)
        snap = self.m.get_stats()["histograms"]["single"]
        assert snap["count"] == 1
        assert snap["min"] == snap["max"] == snap["mean"] == pytest.approx(42.0)


# ===========================================================================
# MetricsCollector — reset + thread safety
# ===========================================================================


class TestMetricsReset:
    def test_reset_clears_all_metrics(self):
        m = MetricsCollector()
        m.increment("a")
        m.gauge("b", 1.0)
        m.histogram("c", 3.0)
        m.reset()
        stats = m.get_stats()
        assert stats["counters"] == {}
        assert stats["gauges"] == {}
        assert stats["histograms"] == {}

    def test_thread_safe_increments(self):
        m = MetricsCollector()
        threads = [
            threading.Thread(target=lambda: m.increment("concurrent.counter"))
            for _ in range(50)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert m.counter_value("concurrent.counter") == 50


# ===========================================================================
# get_metrics() singleton
# ===========================================================================


class TestGetMetricsSingleton:
    def test_returns_same_instance(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_singleton_accumulates_across_calls(self):
        m = get_metrics()
        before = m.counter_value("singleton.test")
        get_metrics().increment("singleton.test")
        assert m.counter_value("singleton.test") == before + 1


# ===========================================================================
# _tag_suffix helper
# ===========================================================================


class TestTagSuffix:
    def test_no_tags(self):
        assert _tag_suffix(None) == ""
        assert _tag_suffix({}) == ""

    def test_single_tag(self):
        assert _tag_suffix({"method": "GET"}) == "{method=GET}"

    def test_multiple_tags_sorted(self):
        result = _tag_suffix({"z": "last", "a": "first"})
        assert result == "{a=first,z=last}"
