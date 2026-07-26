"""FastAPI middleware for trace context, request ID, and timing."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import structlog

from libs.observability.logging import get_logger

logger = get_logger("middleware")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Add correlation ID, timing, and structured logging to every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 1),
            )
            return response

        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "request_failed",
                duration_ms=round(duration_ms, 1),
            )
            raise
