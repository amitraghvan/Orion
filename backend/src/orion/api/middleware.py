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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces aerospace-grade security headers on all HTTP responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # 1. Content Type Options (prevents MIME type sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Clickjacking Protection
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 4. Content Security Policy (allows local WebSocket and Vite frontend)
        csp = (
            "default-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        # 5. Permissions Policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # 6. Cache Control for sensitive API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"

        return response
