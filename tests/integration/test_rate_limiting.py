from __future__ import annotations

from flask import Flask, jsonify

from infrastructure.api.decorators import rate_limit
from infrastructure.api.rate_limiter import InMemorySlidingWindowRateLimiter


def _make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["RATE_LIMIT_ENABLED"] = True
    return app


def test_rate_limit_blocks_after_limit() -> None:
    app = _make_app()
    limiter = InMemorySlidingWindowRateLimiter()

    @app.route("/limited", methods=["GET"])
    @rate_limit(limit=2, window_seconds=60, strategy="ip", limiter=limiter)
    def limited():
        return jsonify({"ok": True}), 200

    client = app.test_client()
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200

    blocked = client.get("/limited")
    assert blocked.status_code == 429
    assert blocked.json["error"] == "Rate limit exceeded"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_rate_limit_endpoint_scope_isolated() -> None:
    app = _make_app()
    limiter = InMemorySlidingWindowRateLimiter()

    @app.route("/a", methods=["GET"])
    @rate_limit(limit=1, window_seconds=60, strategy="ip", scope="endpoint", limiter=limiter)
    def route_a():
        return jsonify({"route": "a"}), 200

    @app.route("/b", methods=["GET"])
    @rate_limit(limit=1, window_seconds=60, strategy="ip", scope="endpoint", limiter=limiter)
    def route_b():
        return jsonify({"route": "b"}), 200

    client = app.test_client()
    assert client.get("/a").status_code == 200
    assert client.get("/b").status_code == 200
    assert client.get("/a").status_code == 429


def test_rate_limit_global_scope_shared() -> None:
    app = _make_app()
    limiter = InMemorySlidingWindowRateLimiter()

    @app.route("/a", methods=["GET"])
    @rate_limit(limit=2, window_seconds=60, strategy="ip", scope="global", limiter=limiter)
    def route_a():
        return jsonify({"route": "a"}), 200

    @app.route("/b", methods=["GET"])
    @rate_limit(limit=2, window_seconds=60, strategy="ip", scope="global", limiter=limiter)
    def route_b():
        return jsonify({"route": "b"}), 200

    client = app.test_client()
    assert client.get("/a").status_code == 200
    assert client.get("/b").status_code == 200
    assert client.get("/a").status_code == 429


def test_rate_limit_disabled_via_config() -> None:
    app = _make_app()
    app.config["RATE_LIMIT_ENABLED"] = False
    limiter = InMemorySlidingWindowRateLimiter()

    @app.route("/limited", methods=["GET"])
    @rate_limit(limit=1, window_seconds=60, strategy="ip", limiter=limiter)
    def limited():
        return jsonify({"ok": True}), 200

    client = app.test_client()
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
