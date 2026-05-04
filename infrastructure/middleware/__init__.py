"""infrastructure/middleware/ — Flask request/response middleware."""

from infrastructure.middleware.request_logger import register_request_logging

__all__ = ["register_request_logging"]
