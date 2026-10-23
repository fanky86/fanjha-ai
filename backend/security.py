from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request

from backend.config import settings


class RateLimiter:
    """Simple in-memory token bucket per key."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.time()
        bucket = self._events[key]
        while bucket and bucket[0] < now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


_build_limiter = RateLimiter(limit=settings.rate_limit_builds_per_minute, window_seconds=60)


def build_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    if not _build_limiter.check(client):
        raise HTTPException(status_code=429, detail="Too many build requests, slow down")


def verify_csrf_token(token: str | None) -> None:
    """Simple CSRF protection: token must equal a per-session signature.

    For a local-only app, we simply verify a header matches a constant derived
    from the configured secret. This prevents cross-site form posts from
    non-local origins that don't know the secret.
    """
    expected = settings.csrf_secret
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def require_csrf(request: Request) -> None:
    token = request.headers.get("X-CSRF-Token")
    verify_csrf_token(token)


def get_csrf_token() -> str:
    return settings.csrf_secret
