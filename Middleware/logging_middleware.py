"""Middleware that logs every incoming HTTP request and its outcome."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("ghostwatcher.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code, duration, and a request ID.

    The webhook secret path segment is redacted from logs so it never
    ends up in log files or aggregation systems.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        safe_path = self._redact_secret(request.url.path)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "request_id=%s method=%s path=%s duration_ms=%.2f status=UNHANDLED_ERROR",
                request_id,
                request.method,
                safe_path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
            request_id,
            request.method,
            safe_path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _redact_secret(path: str) -> str:
        """Replace the secret segment of ``/webhook/<secret>`` with ``***``."""
        parts = path.split("/")
        if len(parts) >= 3 and parts[1] == "webhook":
            parts[2] = "***"
        return "/".join(parts)

