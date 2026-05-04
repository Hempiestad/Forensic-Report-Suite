"""Rate limiting decorators for Flask endpoints."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from flask import current_app, jsonify, request

from infrastructure.api.rate_limiter import InMemorySlidingWindowRateLimiter


# Singleton process-local limiter instance used by decorator defaults.
_default_limiter = InMemorySlidingWindowRateLimiter()


def _extract_identity() -> Optional[str]:
    """Best-effort extraction of current user identity for per-user limits."""
    try:
        from flask_jwt_extended import get_jwt_identity

        ident = get_jwt_identity()
        if isinstance(ident, dict):
            username = ident.get("username")
            if username:
                return str(username)
        if ident:
            return str(ident)
    except Exception:
        return None
    return None


def _request_ip() -> str:
    # Respect proxy headers first when present.
    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def rate_limit(
    *,
    limit: int,
    window_seconds: int,
    strategy: str = "user_or_ip",
    scope: str = "endpoint",
    limiter: Optional[InMemorySlidingWindowRateLimiter] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate a Flask endpoint with rate limiting.

    Args:
        limit: max requests in the window.
        window_seconds: rolling window size in seconds.
        strategy: one of {"ip", "user", "user_or_ip"}.
        scope: "endpoint" (default) or "global".
        limiter: override limiter instance (useful for tests).
    """

    if limit <= 0:
        raise ValueError("limit must be > 0")
    if window_seconds <= 0:
        raise ValueError("window_seconds must be > 0")
    if strategy not in {"ip", "user", "user_or_ip"}:
        raise ValueError("strategy must be one of: ip, user, user_or_ip")
    if scope not in {"endpoint", "global"}:
        raise ValueError("scope must be one of: endpoint, global")

    rl = limiter or _default_limiter

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        endpoint_id = f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if not bool(current_app.config.get("RATE_LIMIT_ENABLED", True)):
                return func(*args, **kwargs)

            user = _extract_identity()
            ip = _request_ip()

            if strategy == "ip":
                actor = f"ip:{ip}"
            elif strategy == "user":
                actor = f"user:{user or 'anonymous'}"
            else:
                actor = f"user:{user}" if user else f"ip:{ip}"

            scoped_endpoint = "*" if scope == "global" else endpoint_id
            bucket = f"{actor}|{scoped_endpoint}"
            decision = rl.check_and_consume(bucket, limit=limit, window_seconds=window_seconds)
            if not decision.allowed:
                response = jsonify(
                    {
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window_seconds": window_seconds,
                        "retry_after_seconds": decision.retry_after_seconds,
                    }
                )
                response.status_code = 429
                response.headers["Retry-After"] = str(decision.retry_after_seconds)
                return response

            response = func(*args, **kwargs)
            return response

        return wrapper

    return decorator
