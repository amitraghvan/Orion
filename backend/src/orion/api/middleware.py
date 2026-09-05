"""FastAPI middleware for telemetry correlation and structured request logging."""

import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from orion.core.logger import get_logger, set_correlation_id

logger = get_logger("orion.api.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Binds or generates an X-Correlation-ID header for end-to-end request tracing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        set_correlation_id(correlation_id)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"

        return response
