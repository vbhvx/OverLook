# backend/app/core/middleware.py
"""
Pure-ASGI middleware. Written against the raw ASGI interface rather than
Starlette's BaseHTTPMiddleware so streaming responses (SSE) pass through
without buffering.
"""
import json
import logging
import math
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.core.logging import request_id_ctx
from backend.app.core.metrics import HTTP_LATENCY, HTTP_REQUESTS, RATE_LIMITED

logger = logging.getLogger("overlook.http")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
UNMATCHED_ROUTE = "__unmatched__"


def _header(scope: Scope, name: bytes) -> Optional[str]:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


def client_ip(scope: Scope, trusted_proxies: int) -> str:
    """
    Resolve the client address. With N trusted reverse proxies in front of us,
    the real client is the Nth entry from the right of X-Forwarded-For; any
    entries further left were supplied by the client and cannot be trusted.
    """
    peer = (scope.get("client") or ("unknown", 0))[0]
    if trusted_proxies <= 0:
        return peer
    xff = _header(scope, b"x-forwarded-for")
    if not xff:
        return peer
    hops = [h.strip() for h in xff.split(",") if h.strip()]
    if len(hops) >= trusted_proxies:
        return hops[-trusted_proxies]
    return hops[0] if hops else peer


class RequestContextMiddleware:
    """Assigns a request ID, logs one line per request, and records metrics."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, b"x-request-id")
        request_id = incoming if incoming and _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_holder: Dict[str, Any] = {"status": 500, "started": False}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                status_holder["started"] = True
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # Handled here rather than by Starlette's outermost error middleware so the
            # response, the log line and the metric all carry this request's ID.
            logger.exception("unhandled error", extra={"path": scope["path"]})
            if status_holder.get("started"):
                raise
            status_holder["status"] = 500
            body = json.dumps({
                "error": "internal_error",
                "message": "Internal server error",
                "requestId": request_id,
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"application/json"), (b"x-request-id", request_id.encode())],
            })
            await send({"type": "http.response.body", "body": body})
        finally:
            elapsed = time.perf_counter() - start
            # Label by route template ("/signals/{signal_id}"), never the raw path,
            # so metric cardinality stays bounded no matter what clients request.
            route = getattr(scope.get("route"), "path", None) or UNMATCHED_ROUTE
            method = scope["method"]
            status = status_holder["status"]
            HTTP_REQUESTS.labels(method, route, str(status)).inc()
            HTTP_LATENCY.labels(method, route).observe(elapsed)
            if route not in ("/metrics",) and not route.startswith("/api/v1/health"):
                logger.info(
                    "request",
                    extra={
                        "method": method,
                        "path": scope["path"],
                        "route": route,
                        "status": status,
                        "durationMs": round(elapsed * 1000, 2),
                    },
                )
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware:
    HEADERS: List[Tuple[bytes, bytes]] = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"cross-origin-opener-policy", b"same-origin"),
    ]

    def __init__(self, app: ASGIApp, hsts: bool = False):
        self.app = app
        self.headers = list(self.HEADERS)
        if hsts:
            self.headers.append((b"strict-transport-security", b"max-age=63072000; includeSubDomains"))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + self.headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class TokenBucketLimiter:
    """
    Per-key token bucket. In-process by design: each replica enforces its own
    budget. A shared limit across replicas would move this state to Redis or
    to the edge (CDN/WAF), behind the same `allow()` interface.
    """

    def __init__(
        self,
        rate_per_sec: float,
        burst: int,
        max_keys: int = 50_000,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.rate = rate_per_sec
        self.burst = float(burst)
        self.max_keys = max_keys
        self._clock = clock
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def allow(self, key: str) -> Tuple[bool, float]:
        """Returns (allowed, seconds_until_next_token)."""
        now = self._clock()
        tokens, last = self._buckets.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            allowed, wait = True, 0.0
        else:
            self._buckets[key] = (tokens, now)
            allowed, wait = False, (1.0 - tokens) / self.rate
        if len(self._buckets) > self.max_keys:
            self._evict_full(now)
        return allowed, wait

    def _evict_full(self, now: float) -> None:
        # A bucket that has refilled completely carries no state worth keeping.
        refill_time = self.burst / self.rate
        stale = [k for k, (_, last) in self._buckets.items() if now - last >= refill_time]
        for k in stale:
            del self._buckets[k]


class RateLimitMiddleware:
    EXEMPT_PREFIXES = ("/metrics", "/api/v1/health", "/api/v1/stream")

    def __init__(self, app: ASGIApp, limiter: TokenBucketLimiter, trusted_proxies: int = 1):
        self.app = app
        self.limiter = limiter
        self.trusted_proxies = trusted_proxies

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(self.EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        allowed, wait = self.limiter.allow(client_ip(scope, self.trusted_proxies))
        if allowed:
            await self.app(scope, receive, send)
            return

        RATE_LIMITED.inc()
        body = json.dumps({
            "error": "rate_limited",
            "message": "Too many requests",
            "requestId": request_id_ctx.get(),
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"retry-after", str(max(1, math.ceil(wait))).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
