# System Architecture

## Runtime topology

```text
                 ┌──────────────── upstream providers ────────────────┐
                 │  USGS · OpenSky · Open-Meteo · curated samples      │
                 └───────────────────────────┬─────────────────────────┘
                                             │ HTTPS (per-source cadence)
   ┌─────────────────────────────────────────▼──────────────────────────────┐
   │ worker ×N    scheduler → circuit breaker → adapter → validate → upsert  │
   │              one leader via pg_try_advisory_lock; others stand by       │
   │              :9100/metrics                                              │
   └──────────────┬───────────────────────────────────────┬─────────────────┘
                  │ SQL                                   │ pg_notify
   ┌──────────────▼───────────────────────────────────────▼─────────────────┐
   │ PostgreSQL 16 + PostGIS 3.4                                            │
   │   signals (GiST geometry + geography) · source_state · sync_runs       │
   └──────────────▲───────────────────────────────────────┬─────────────────┘
                  │ SQL (pooled)                          │ LISTEN
   ┌──────────────┴───────────────────────────────────────▼─────────────────┐
   │ api ×N (stateless)   REST /api/v1 · SSE /api/v1/stream · /metrics       │
   └──────────────▲──────────────────────────────────────────────────────────┘
                  │ /api  (X-Forwarded-For, request ID, SSE unbuffered)
   ┌──────────────┴─────────────────────────────┐
   │ web: nginx (CSP, caching) + React/MapLibre │
   └────────────────────────────────────────────┘
```

A single process mode also exists for development. With `DATABASE_URL=memory://` the API runs the scheduler in-process against the in-memory store, and events fan out in-process.

## Code structure

| Package | Responsibility | Depends on |
|---|---|---|
| `api/` | Routing, parameter parsing, error envelope, dependency wiring | services through `deps.py` only |
| `container.py` | Composition root: builds store, bus, ingestion and correlation from settings | everything |
| `ingestion/` | Registry (static metadata and cadence), pipeline service, scheduler, leader election | storage contract, providers, core |
| `correlation/` | Versioned proximity rules producing relations and events | storage contract |
| `storage/` | `SignalStore` contract plus memory and PostGIS engines | schemas |
| `providers/` | One adapter per upstream source: fetch and parse into `SignalEnvelope` | schemas, geospatial |
| `core/` | Cross-cutting concerns: logging, metrics, middleware, resilience, event bus | — |

Nothing outside `container.py` constructs infrastructure, and endpoints receive collaborators through FastAPI `Depends`. That is what lets tests build the whole app around fakes (`build_container(settings, adapters={...})`).

## Invariants

1. **The map is a presentation layer, not the truth.** The UI renders stored, validated records. It never interpolates or invents positions.
2. **Provider isolation.** Each source has its own lock, circuit breaker, backoff state and timeout. One provider's failure is recorded and reported but never propagates.
3. **Temporal normalization.** Observation, publication, ingestion and validity times are distinct fields, all timezone-aware UTC. Revisions never overwrite the original ingestion time.
4. **Spatial correctness.** Coordinates are WGS84 `[lon, lat]`. Reversed or non-finite coordinates are rejected. Bboxes crossing the antimeridian are supported end to end.
5. **Honest provenance.** Simulated data is labelled at the record level and enforced by a test. A failed fetch never re-stamps cached data as fresh.
6. **Proximity is not causation.** Correlations carry their measured criteria and a disclaimer, and confidence is capped at `observational_association`.

## Failure modes

| Failure | Behaviour |
|---|---|
| Provider times out / 5xx / 429 | Run recorded as `failed`. Exponential backoff with jitter (15 s base, capped at the source's interval). After `CIRCUIT_FAILURE_THRESHOLD` consecutive failures the circuit opens for `CIRCUIT_RESET_SECONDS`, then one half-open trial runs. |
| Worker leader crashes | Its Postgres session ends and the advisory lock is released. A standby acquires it within 10 s and does a full sync. |
| Database unreachable | `/health/ready` returns 503, so load balancers stop routing. `/health/live` stays 200, so the orchestrator does not restart-loop. The scheduler logs the failure and retries on its next tick. |
| Event listener connection drops | Reconnects every 2 s. Browsers fall back to 60 s polling while their stream is down. |
| Slow SSE client | Its bounded queue drops oldest events. Other clients are unaffected. |
| Client floods the API | Per-IP token bucket returns 429 with `Retry-After`. Manual sync has its own per-source cooldown. |
| Unhandled exception | 500 with the error envelope and request ID. The stack trace is logged, never returned. |

## Scaling notes

- **API:** stateless; scale horizontally. Each replica uses one pooled engine (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) and one `LISTEN` connection.
- **Worker:** extra replicas add availability, not throughput. If ingestion outgrows one process, the advisory lock can be keyed per source to spread sources across workers.
- **Database:** bbox and radius queries are index-backed. `signals` size is bounded by retention. The read pattern (recent, spatial) suits time-based partitioning if volume grows by orders of magnitude.
- **Rate limiting** is per replica. A global limit belongs at the edge or in Redis behind the same `allow()` interface.

Decision records: [`docs/adr/`](adr/README.md).
