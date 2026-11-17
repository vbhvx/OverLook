# backend/tests/test_resilience.py
import pytest

from backend.app.core.middleware import TokenBucketLimiter, client_ip
from backend.app.core.resilience import CircuitBreaker, CircuitOpenError, CircuitState, backoff_delay


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_breaker_opens_after_threshold_then_half_opens_after_timeout():
    clock = FakeClock()
    br = CircuitBreaker(failure_threshold=3, reset_timeout=60, clock=clock)
    for _ in range(2):
        br.record_failure()
    assert br.state == CircuitState.CLOSED
    br.record_failure()
    assert br.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError) as exc:
        br.before_call()
    assert exc.value.retry_after == pytest.approx(60)

    clock.now = 61
    assert br.state == CircuitState.HALF_OPEN
    br.before_call()  # trial call allowed


def test_half_open_failure_reopens_immediately():
    clock = FakeClock()
    br = CircuitBreaker(failure_threshold=3, reset_timeout=60, clock=clock)
    for _ in range(3):
        br.record_failure()
    clock.now = 61
    assert br.state == CircuitState.HALF_OPEN
    br.record_failure()
    assert br.state == CircuitState.OPEN


def test_success_resets_breaker():
    br = CircuitBreaker(failure_threshold=2, reset_timeout=60, clock=FakeClock())
    br.record_failure()
    br.record_success()
    br.record_failure()
    assert br.state == CircuitState.CLOSED
    assert br.consecutive_failures == 1


@pytest.mark.parametrize("attempt", range(8))
def test_backoff_is_bounded_and_jittered(attempt):
    lo = backoff_delay(attempt, base=10, cap=300, rng=lambda: 0.0)
    hi = backoff_delay(attempt, base=10, cap=300, rng=lambda: 1.0)
    expected = min(300, 10 * 2 ** attempt)
    assert lo == pytest.approx(expected / 2)
    assert hi == pytest.approx(expected)


def test_token_bucket_allows_burst_then_refills():
    clock = FakeClock()
    limiter = TokenBucketLimiter(rate_per_sec=1.0, burst=3, clock=clock)
    assert [limiter.allow("ip")[0] for _ in range(4)] == [True, True, True, False]
    allowed, wait = limiter.allow("ip")
    assert not allowed and wait == pytest.approx(1.0)
    clock.now = 1.0
    assert limiter.allow("ip")[0] is True
    assert limiter.allow("other-ip")[0] is True, "buckets are per key"


def test_token_bucket_evicts_idle_keys():
    clock = FakeClock()
    limiter = TokenBucketLimiter(rate_per_sec=1.0, burst=2, max_keys=10, clock=clock)
    for i in range(11):
        limiter.allow(f"k{i}")
    clock.now = 100
    limiter.allow("fresh")
    assert len(limiter._buckets) <= 2


def _scope(peer, xff=None):
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return {"client": (peer, 1234), "headers": headers}


def test_client_ip_ignores_spoofed_forwarded_for_entries():
    # Client sent "6.6.6.6"; our one trusted proxy appended the real peer.
    scope = _scope("10.0.0.2", "6.6.6.6, 203.0.113.9")
    assert client_ip(scope, trusted_proxies=1) == "203.0.113.9"
    assert client_ip(scope, trusted_proxies=0) == "10.0.0.2"
    assert client_ip(_scope("10.0.0.2"), trusted_proxies=1) == "10.0.0.2"
