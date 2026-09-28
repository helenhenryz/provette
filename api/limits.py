"""Rate limits, in memory: enough for one container behind one address.

A `RateLimit(n, per_s)` allows `n` calls per client key in any window of `per_s` seconds. The
key is the client's address (Fly's proxy sets `Fly-Client-IP`; `X-Forwarded-For` otherwise).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def client_key(request: Request) -> str:
    for header in ("fly-client-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimit:
    def __init__(self, n: int, per_s: float) -> None:
        self.n = n
        self.per_s = per_s
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> bool:
        """True if the call may go ahead (and it is counted); False if the limit is reached."""
        t = time.time() if now is None else now
        with self._lock:
            calls = self._calls[key]
            while calls and calls[0] <= t - self.per_s:
                calls.popleft()
            if len(calls) >= self.n:
                return False
            calls.append(t)
            return True

    def guard(self, request: Request, what: str) -> None:
        if not self.check(client_key(request)):
            raise HTTPException(
                429,
                f"Too many {what} from this address: at most {self.n} every "
                f"{self.per_s:.0f} seconds. Wait a moment and try again.",
            )
