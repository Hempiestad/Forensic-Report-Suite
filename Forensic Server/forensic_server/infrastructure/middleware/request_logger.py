from __future__ import annotations

import time

from flask import Flask, g, request

from ..observability import bind_request_id, get_logger, get_metrics


_log = get_logger(__name__)


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def _before_request() -> None:
        g._request_start_time = time.perf_counter()
        bind_request_id(request.headers.get("X-Request-ID"))

    @app.after_request
    def _after_request(response):
        started = getattr(g, "_request_start_time", None)
        duration_ms = 0.0
        if started is not None:
            duration_ms = round((time.perf_counter() - started) * 1000.0, 3)

        endpoint = request.endpoint or request.path
        metrics = get_metrics()
        metrics.increment("http_requests", tags={"method": request.method, "endpoint": endpoint, "status": str(response.status_code)})
        metrics.histogram("http_latency_ms", duration_ms, tags={"method": request.method, "endpoint": endpoint})

        _log.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.path,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "remote_addr": request.remote_addr,
            },
        )
        return response
