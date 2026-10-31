"""Resilience: retries with backoff, rate limiting, circuit breaking.

Boring on purpose. Every rule here exists because a provider exhibited the
behavior: DeepInfra 429s while autoscaling (retry after a short delay),
TypeSafe documents 529 Overloaded and follows retry-after, MiniMax enforces
200 RPM. All timing is injectable so tests run in microseconds.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field


class RetryExhausted(RuntimeError):
    """All attempts failed; the last error is attached."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"exhausted {attempts} attempts: {last_error!r}")


@dataclass
class RetryPolicy:
    """Exponential backoff with jitter; honors Retry-After when present."""

    max_attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 20.0
    jitter: float = 0.3
    sleeper: Callable[[float], None] = field(default_factory=lambda: time.sleep)
    rng: random.Random = field(default_factory=random.Random)

    def delay_for(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.max_delay * 4)
        raw = self.base_delay * (2**attempt)
        raw = min(raw, self.max_delay)
        jitter_span = raw * self.jitter
        return max(0.0, raw + self.rng.uniform(-jitter_span, jitter_span))

    def run(self, fn: Callable[[], object], should_retry: Callable[[Exception], bool]) -> object:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - re-raised below
                last_error = exc
                if not should_retry(exc) or attempt == self.max_attempts - 1:
                    raise
                self.sleeper(self.delay_for(attempt, getattr(exc, "retry_after", None)))
        raise RetryExhausted(self.max_attempts, last_error)  # pragma: no cover


class TokenBucket:
    """Rate limiter: ``rate`` tokens/sec, bursting up to ``capacity``."""

    def __init__(self, rate: float, capacity: float, clock: Callable[[], float] = time.monotonic):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.clock = clock
        self._last = clock()

    def try_acquire(self, amount: float = 1.0) -> bool:
        """Non-blocking: take ``amount`` tokens if available right now."""
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.rate)
        self._last = now
        if amount > self.capacity or amount > self.tokens:
            return False
        self.tokens -= amount
        return True

    def acquire(self, amount: float = 1.0, blocker: Callable[[float], None] = time.sleep) -> bool:
        """Take ``amount`` tokens, blocking until available. False if the
        amount exceeds capacity entirely (a programming error upstream)."""
        if amount > self.capacity:
            return False
        while not self.try_acquire(amount):
            blocker(0.001)  # tiny sleeps keep tests fast with a fake clock
        return True


class CircuitBreaker:
    """Trip after ``threshold`` consecutive failures; half-open after ``reset_after``."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __init__(
        self,
        threshold: int = 5,
        reset_after: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.threshold = threshold
        self.reset_after = reset_after
        self.clock = clock
        self.failures = 0
        self.state = self.CLOSED
        self._opened_at: float | None = None

    def allow(self) -> bool:
        if self.state == self.OPEN:
            assert self._opened_at is not None
            if self.clock() - self._opened_at >= self.reset_after:
                self.state = self.HALF_OPEN
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.state = self.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold or self.state == self.HALF_OPEN:
            self.state = self.OPEN
            self._opened_at = self.clock()
