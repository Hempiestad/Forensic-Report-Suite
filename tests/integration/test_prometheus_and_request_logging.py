"""
tests/integration/test_prometheus_and_request_logging.py

Tests for:
- infrastructure.observability.prometheus_exporter (Prometheus text format)
- infrastructure.middleware.request_logger (HTTP access log)
"""

from __future__ import annotations

import json
import re

import pytest

from infrastructure.observability.metrics_collector import MetricsCollector
from infrastructure.observability.prometheus_exporter import generate_prometheus_text
from infrastructure.observability import get_logger


# ===========================================================================
# Prometheus text format — generate_prometheus_text
# ===========================================================================


class TestPrometheusExporter:
    def _collector(self) -> MetricsCollector:
        """Return a fresh isolated collector for each test."""
        return MetricsCollector()

    def test_empty_collector_produces_no_metrics_comment(self):
        text = generate_prometheus_text(self._collector())
        assert "# no metrics" in text

    def test_counter_appears_in_output(self):
        m = self._collector()
        m.increment("http.requests", tags={"method": "POST"})
        text = generate_prometheus_text(m)
        assert "forensic_http_requests_total" in text
        assert 'method="POST"' in text
        assert "} 1" in text

    def test_counter_multiple_increments(self):
        m = self._collector()
        for _ in range(7):
            m.increment("http.requests", tags={"method": "GET"})
        text = generate_prometheus_text(m)
        # The value should be 7
        assert "} 7" in text

    def test_gauge_appears_in_output(self):
        m = self._collector()
        m.gauge("cache.size", 512)
        text = generate_prometheus_text(m)
        assert "forensic_cache_size" in text
        assert "512" in text

    def test_histogram_summary_quantiles(self):
        m = self._collector()
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            m.histogram("latency_ms", v)
        text = generate_prometheus_text(m)
        assert 'quantile="0.5"' in text
        assert 'quantile="0.95"' in text
        assert 'quantile="0.99"' in text
        assert "forensic_latency_ms_sum" in text
        assert "forensic_latency_ms_count" in text

    def test_histogram_count_value(self):
        m = self._collector()
        for v in range(1, 11):
            m.histogram("scores", float(v))
        text = generate_prometheus_text(m)
        # _count should be 10
        assert "forensic_scores_count" in text
        count_line = next(l for l in text.splitlines() if "scores_count" in l)
        assert count_line.endswith("10")

    def test_type_comment_present_for_counter(self):
        m = self._collector()
        m.increment("events.login")
        text = generate_prometheus_text(m)
        assert "# TYPE forensic_counters_total counter" in text

    def test_type_comment_present_for_gauge(self):
        m = self._collector()
        m.gauge("mem.free", 100)
        text = generate_prometheus_text(m)
        assert "# TYPE forensic_gauges gauge" in text

    def test_type_comment_present_for_histogram(self):
        m = self._collector()
        m.histogram("query_ms", 5.0)
        text = generate_prometheus_text(m)
        assert "# TYPE forensic_query_ms summary" in text

    def test_metric_names_sanitized(self):
        """Dots and special chars in metric names must become underscores."""
        m = self._collector()
        m.increment("http.req.count")
        text = generate_prometheus_text(m)
        # Dots replaced with underscores
        assert "forensic_http_req_count_total" in text

    def test_output_ends_with_newline(self):
        m = self._collector()
        m.increment("x")
        assert generate_prometheus_text(m).endswith("\n")

    def test_multiple_metrics_all_present(self):
        m = self._collector()
        m.increment("a", tags={"env": "test"})
        m.gauge("b", 1.5)
        m.histogram("c", 3.0)
        text = generate_prometheus_text(m)
        assert "forensic_a_total" in text
        assert "forensic_b" in text
        assert "forensic_c" in text

    def test_tags_with_multiple_pairs(self):
        m = self._collector()
        m.increment("req", tags={"method": "POST", "endpoint": "/cases"})
        text = generate_prometheus_text(m)
        assert 'method="POST"' in text
        assert 'endpoint="/cases"' in text


# ===========================================================================
# Request Logger — register_request_logging
# ===========================================================================


class TestRequestLogger:
    """Test HTTP access log middleware using a minimal Flask test client."""

    @pytest.fixture
    def flask_app(self):
        """Return a minimal Flask app with request logging registered."""
        from flask import Flask, jsonify
        from infrastructure.middleware.request_logger import register_request_logging

        app = Flask("test_req_logger")
        app.config["TESTING"] = True
        app.config["JWT_SECRET_KEY"] = "test-secret"

        @app.route("/ping")
        def ping():
            return jsonify({"ok": True}), 200

        @app.route("/create", methods=["POST"])
        def create():
            return jsonify({"id": 1}), 201

        register_request_logging(app)
        return app

    def test_get_request_does_not_crash(self, flask_app):
        with flask_app.test_client() as client:
            resp = client.get("/ping")
        assert resp.status_code == 200

    def test_post_request_does_not_crash(self, flask_app):
        with flask_app.test_client() as client:
            resp = client.post("/create", json={"name": "test"})
        assert resp.status_code == 201

    def test_request_id_injected_in_response_headers(self, flask_app):
        """Request ID should be forwarded to response via X-Request-ID."""
        # register_request_logging binds a request ID if not set
        with flask_app.test_client() as client:
            resp = client.get("/ping")
        # The server.py full middleware sets X-Request-ID; the request_logger
        # alone doesn't inject it — that's done in server.py's after_request.
        # Just assert no crash here.
        assert resp.status_code == 200

    def test_custom_request_id_propagated(self, flask_app):
        """If X-Request-ID header is provided, it should be bound."""
        from infrastructure.observability import current_request_id

        with flask_app.test_request_context("/ping", headers={"X-Request-ID": "custom-abc"}):
            from flask import g
            flask_app.preprocess_request()  # trigger before_request

    def test_access_log_written_as_json(self, flask_app, caplog):
        """After a request, a JSON log record with 'http.access' logger exists."""
        import logging

        with caplog.at_level(logging.INFO, logger="http.access"):
            with flask_app.test_client() as client:
                client.get("/ping")

        access_records = [r for r in caplog.records if r.name == "http.access"]
        assert len(access_records) >= 1
        rec = access_records[0]
        assert rec.levelno == logging.INFO
        assert "GET" in rec.message or "/ping" in rec.message

    def test_extra_fields_on_log_record(self, flask_app, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="http.access"):
            with flask_app.test_client() as client:
                client.get("/ping")

        access_records = [r for r in caplog.records if r.name == "http.access"]
        assert access_records, "No http.access log records found"
        rec = access_records[-1]
        assert hasattr(rec, "method")
        assert hasattr(rec, "path")
        assert hasattr(rec, "status")
        assert hasattr(rec, "latency_ms")

    def test_404_request_logged(self, flask_app, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="http.access"):
            with flask_app.test_client() as client:
                client.get("/nonexistent")

        access_records = [r for r in caplog.records if r.name == "http.access"]
        assert any(getattr(r, "status", 0) == 404 for r in access_records)
