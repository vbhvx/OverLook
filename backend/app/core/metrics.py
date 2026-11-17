# backend/app/core/metrics.py
"""Prometheus metrics shared by the API and the ingestion worker."""
from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "overlook_http_requests_total",
    "HTTP requests processed",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "overlook_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
RATE_LIMITED = Counter(
    "overlook_http_rate_limited_total",
    "Requests rejected by the rate limiter",
)

INGESTION_RUNS = Counter(
    "overlook_ingestion_runs_total",
    "Provider sync runs",
    ["source", "status"],
)
INGESTION_RECORDS = Counter(
    "overlook_ingestion_records_total",
    "Records processed during ingestion, by outcome",
    ["source", "outcome"],  # inserted | updated | unchanged | rejected
)
INGESTION_DURATION = Histogram(
    "overlook_ingestion_duration_seconds",
    "Provider sync duration",
    ["source"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
CIRCUIT_STATE = Gauge(
    "overlook_provider_circuit_state",
    "Provider circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["source"],
)
SIGNALS_PRUNED = Counter(
    "overlook_signals_pruned_total",
    "Signals removed by the retention policy",
)
SSE_CLIENTS = Gauge(
    "overlook_sse_clients",
    "Connected Server-Sent Events clients",
)
