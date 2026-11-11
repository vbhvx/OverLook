# backend/app/core/resilience.py
"""
Failure-handling primitives for upstream providers.

A provider that is down should cost us one cheap rejection per cycle, not a
10-second timeout per cycle, and it must not slow down healthy providers.
"""
import random
import time
from enum import Enum
from typing import Callable, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


CIRCUIT_STATE_VALUE = {CircuitState.CLOSED: 0, CircuitState.HALF_OPEN: 1, CircuitState.OPEN: 2}


class CircuitOpenError(Exception):
    def __init__(self, retry_after: float):
        super().__init__(f"Circuit open; retry in {retry_after:.0f}s")
        self.retry_after = retry_after


class CircuitBreaker:
    """
    Classic three-state breaker.

    CLOSED    — calls pass through; consecutive failures are counted.
    OPEN      — calls are rejected until `reset_timeout` has elapsed.
    HALF_OPEN — one trial call is allowed; success closes, failure re-opens.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if self._clock() - self._opened_at >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._failures

    def before_call(self) -> None:
        if self.state == CircuitState.OPEN and self._opened_at is not None:
            remaining = self.reset_timeout - (self._clock() - self._opened_at)
            raise CircuitOpenError(max(remaining, 0.0))

    def record_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self.state == CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = self._clock()


def backoff_delay(
    attempt: int,
    base: float,
    cap: float,
    rng: Callable[[], float] = random.random,
) -> float:
    """
    Exponential backoff with "equal jitter": half the delay is fixed, half random.
    Jitter keeps many workers that failed together from retrying in lockstep.
    """
    exp = min(cap, base * (2 ** max(attempt, 0)))
    return exp / 2 + rng() * (exp / 2)
