"""
Simple in-memory, per-IP sliding-window rate limiter.

This is intentionally lightweight for a single-process dev/testnet
deployment. A production deployment running multiple worker processes
or instances would need a shared store (Redis, etc.) instead — this
in-memory version does not coordinate across processes.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

_EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

# Module-level (not instance-level) so tests can reset it between runs —
# the FastAPI `app` object, and therefore this middleware instance, is a
# long-lived singleton across an entire test session.
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    """Test-only helper: clears all tracked request timestamps."""
    _hits.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_requests

        hits = _hits[client_ip]
        while hits and now - hits[0] > window:
            hits.popleft()

        if len(hits) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again shortly."},
            )

        hits.append(now)
        return await call_next(request)
