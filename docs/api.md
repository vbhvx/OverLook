# OverLook REST API Specification (v1)

Base URL: `/api/v1`

## Endpoints

### 1. `GET /api/v1/health`
Returns service readiness, active signal counts, and registered source health statuses.

**Response**:
```json
{
  "status": "healthy",
  "service": "OverLook - Public Signal Intelligence",
  "version": "1.1.0",
  "environment": "development",
  "store": "postgis",
  "storeReachable": true,
  "activeSignals": 142,
  "degradedSources": [],
  "sources": {
    "usgs-earthquakes": "active",
    "open-meteo": "active",
    "opensky-network": "active"
  },
  "timestamp": "2026-11-10T12:00:00Z"
}
```

### 2. `GET /api/v1/sources`
Lists registered intelligence providers with licensing metadata and operational status.

### 3. `POST /api/v1/sources/{source_id}/sync`
Triggers an immediate synchronization run for a provider adapter. Limited to one call per source every `MANUAL_SYNC_COOLDOWN_SECONDS` (default 60). Extra calls get `429` with `Retry-After`.

`GET /api/v1/sources/{source_id}/runs?limit=10` returns recent sync runs, newest first.

### 4. `GET /api/v1/layers`
Returns available map layers, geometry types, refresh intervals, and active signal counts.

### 5. `GET /api/v1/signals`
Queries signals with multi-parameter filtering:
- `bbox`: `west,south,east,north` (e.g. `-123.5,37.0,-121.5,38.5`). `west > east` means the box crosses the antimeridian. Out-of-range values or `south > north` return `400`.
- `category`: `earthquake`, `weather`, `aircraft`, `vessel`, `satellite`, `camera`, `infrastructure`
- `source`: Provider identifier
- `data_status`: `actual`, `forecast`, `stale`, `delayed`, `simulated`
- `start`, `end`: ISO 8601. Timestamps without an offset are treated as UTC. `start > end` returns `400`.
- `limit`: default 250, clamped to `MAX_QUERY_RESULTS` (1000)
- `offset`: pagination offset. Results are ordered by `observedAt` descending, then `id`, so pages are stable.

An unknown `category` or `data_status` returns `422`.

### 6. `GET /api/v1/signals/{signal_id}`
Retrieves complete signal envelope, SHA-256 fingerprint, source link, and nearby correlated signals within 60km.

### 7. `GET /api/v1/timeline`
Returns histogram frequencies of observations bucketed by time interval.
- Query parameters: `hours` (1 - 168), `interval_hours` (1 - 24, at most `hours`), `category`
- Bucket edges align to multiples of the interval in UTC, so repeated requests return the same buckets.

### 8. `GET /api/v1/events`
Returns rule-derived correlation events: recent earthquakes with observations within 100 km and ±12 h, and preset regions containing at least 3 signals across at least 2 categories. `GET /api/v1/events/{id}` returns one event. Every relation records its measured distance, time delta and rule version. Confidence is always `observational_association`.

### 9. `GET /api/v1/regions`
Returns predefined analytical hotspots (San Francisco Bay, Hawaii, Mediterranean, English Channel, Tokyo Bay, Strait of Malacca).

### 10. `GET /api/v1/map/summary`
Returns global counts, category breakdowns, and status distribution.


### 11. `GET /api/v1/stream`
Server-Sent Events. The server sends `event: ready` on connect, then `event: signals.changed` with `{"sourceId", "inserted", "updated", "at"}` whenever an ingestion run changes data. Keepalive comments arrive every 15 s. Returns `503` once `MAX_SSE_CLIENTS` streams are open.

### 12. Probes and metrics
- `GET /api/v1/health/live`: the process is up. Never touches dependencies.
- `GET /api/v1/health/ready`: `200` when the store answers *and* the schema exists, otherwise `503`.
- `GET /api/v1/health`: human-oriented summary. `status` is `healthy`, `degraded` (some provider failing) or `unhealthy` (store unreachable).
- `GET /metrics`: Prometheus exposition. The worker serves its own on `:9100`.

## Errors

Every error response uses one envelope:

```json
{"error": "not_found", "message": "Signal with ID 'x' not found", "requestId": "4b47a300ca68456abb1958b17ed9e5ce"}
```

`error` is one of `bad_request`, `not_found`, `validation_error` (with `details[]`: `loc`, `msg`, `type`; the input is never echoed back), `rate_limited`, `unavailable` or `internal_error`. `requestId` matches the `X-Request-ID` response header and the server's log lines. A client may send its own `X-Request-ID` (`[A-Za-z0-9._-]{1,128}`) to trace a call end to end.

## Rate limiting

Each client gets a token bucket (`RATE_LIMIT_PER_MINUTE`, burst `RATE_LIMIT_BURST`), keyed by IP as resolved through `TRUSTED_PROXY_COUNT` reverse proxies. Health, metrics and the stream are exempt. A limited request gets `429` with `Retry-After`.
