"""In-memory sliding-window rate limiting (stdlib only).

The API runs as a single process, so process-local memory is enough. Limits are intentionally
generous for real use (a Shortcut fires a few requests a day) and tight for brute force.
"""

import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    def __init__(
        self,
        max_events: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}

    def _recent(self, key: str) -> deque[float]:
        events = self._events.setdefault(key, deque())
        cutoff = self._clock() - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def is_blocked(self, key: str) -> bool:
        return len(self._recent(key)) >= self.max_events

    def hit(self, key: str) -> None:
        self._recent(key).append(self._clock())
        if len(self._events) > 10_000:  # keep memory bounded under a spray of random keys
            self._purge()

    def allow(self, key: str) -> bool:
        """Record an event and return False if the limit is already exhausted."""
        if self.is_blocked(key):
            return False
        self.hit(key)
        return True

    def _purge(self) -> None:
        for key in list(self._events):
            if not self._recent(key):
                del self._events[key]

    def clear(self) -> None:
        self._events.clear()


# Failed API-token logins per client IP: 10 per 5 minutes.
failed_auth_limiter = SlidingWindowLimiter(max_events=10, window_seconds=300)
# Requests per token: 120 per minute.
token_usage_limiter = SlidingWindowLimiter(max_events=120, window_seconds=60)
# Includes invalid and valid Telegram logins: bound expensive HMAC / DB work.
login_limiter = SlidingWindowLimiter(max_events=30, window_seconds=60)


def reset_limiters() -> None:
    failed_auth_limiter.clear()
    token_usage_limiter.clear()
    login_limiter.clear()
