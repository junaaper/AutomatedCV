"""Sliding-window rate limiting as FastAPI dependencies.

State is in-process memory, which is correct for this deployment (a single Render
instance). Running several instances would need a shared store such as Redis, keeping
the same interface.
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Literal

from fastapi import Depends, HTTPException, Request, status

from app.auth.deps import get_current_user
from app.auth.models import User


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._calls = 0

    def hit(self, key: str, limit: int, window: float) -> float | None:
        """Records a hit. Returns seconds until a slot frees up if over the limit."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return hits[0] + window - now
        hits.append(now)
        self._calls += 1
        if self._calls % 1000 == 0:
            self._prune(now, window)
        return None

    def _prune(self, now: float, window: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - window]:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()


def _too_many(retry_after: float) -> HTTPException:
    seconds = max(1, math.ceil(retry_after))
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"Too many requests. Try again in {seconds}s.",
        headers={"Retry-After": str(seconds)},
    )


def rate_limit(
    scope: str, limit: int, window: float = 60, by: Literal["ip", "user"] = "ip"
) -> Callable:
    """e.g. `dependencies=[rate_limit("login", 10)]`: 10 requests/minute per client IP."""
    if by == "user":

        async def by_user(user: User = Depends(get_current_user)) -> None:  # noqa: B008
            if (retry := limiter.hit(f"{scope}:u:{user.id}", limit, window)) is not None:
                raise _too_many(retry)

        return Depends(by_user)

    async def by_ip(request: Request) -> None:
        # Behind Render's proxy, uvicorn --proxy-headers puts the real client IP here.
        ip = request.client.host if request.client else "unknown"
        if (retry := limiter.hit(f"{scope}:ip:{ip}", limit, window)) is not None:
            raise _too_many(retry)

    return Depends(by_ip)
