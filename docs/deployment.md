# Deployment & Operations

## 1. Docker Compose

```bash
cp .env.example .env        # set POSTGRES_PASSWORD and CORS_ORIGINS for anything non-local
docker compose up --build -d
docker compose ps
```

| Service | Role | Port |
|---|---|---|
| `postgis` | PostgreSQL 16 + PostGIS 3.4 | `127.0.0.1:5432` |
| `migrate` | One-shot `alembic upgrade head`, then exits | — |
| `api` | FastAPI, stateless, no in-process ingestion | `127.0.0.1:8000` |
| `worker` | Ingestion scheduler (leader-elected), seeds fixtures | `:9100` metrics, internal |
| `web` | nginx serving the SPA and proxying `/api` | `8080` |
| `prometheus`, `grafana` | `--profile observability` only | `9090`, `3001` |

Startup is ordered by health: PostGIS is ready (probed over TCP) → migrations complete successfully → the API is healthy → web starts. Only `web` is published beyond localhost.

Scale out:

```bash
docker compose up -d --scale api=3      # behind a load balancer of your choice
docker compose up -d --scale worker=2   # second worker waits on the leader lock
```

## 2. Images

Both images are multi-stage and run as non-root users.

- `backend/Dockerfile` is one image with three roles. The default command is the API. Override it with `python -m backend.app.worker`, or `alembic -c backend/alembic.ini upgrade head` for migrations.
- `frontend/Dockerfile` builds with Node 20 and serves from `nginx-unprivileged` on `:8080`.

## 3. Production checklist

- [ ] `ENVIRONMENT=production`. Startup refuses `CORS_ORIGINS=*` and `DEBUG=true` in production.
- [ ] `CORS_ORIGINS` set to the exact public origin(s).
- [ ] `POSTGRES_PASSWORD` comes from a secret store, not the default.
- [ ] `TRUSTED_PROXY_COUNT` equals the number of reverse proxies in front of the API, or rate limiting keys on the wrong IP.
- [ ] TLS terminated at the edge. HSTS is emitted by the API in production.
- [ ] Migrations run as a separate step before new API and worker versions roll out.
- [ ] Load balancer routes on `/api/v1/health/ready`. The orchestrator restarts on `/api/v1/health/live`.
- [ ] Prometheus scrapes `api:8000/metrics` and `worker:9100/metrics`, with `deploy/prometheus/alerts.yml` loaded.
- [ ] Postgres `max_connections` ≥ replicas × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW` + 2).

## 4. Migrations

```bash
DATABASE_URL=postgresql+asyncpg://… alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini downgrade -1      # roll back one revision
alembic -c backend/alembic.ini revision -m "add x"
```

Migrations are hand-written SQL, because PostGIS types and partial or GiST indexes don't autogenerate well. CI runs upgrade → downgrade → upgrade on every change to prove they are reversible.

## 5. Observability

**Logs:** one JSON object per line (`LOG_FORMAT=json`). Every request logs `method`, `route`, `status`, `durationMs` and `requestId`. Every sync logs `source`, `status`, `inserted` and `updated`.

**Key metrics**

| Metric | Use |
|---|---|
| `overlook_http_requests_total{method,route,status}` | Traffic and error ratio (route is the template, so cardinality stays bounded) |
| `overlook_http_request_duration_seconds` | Latency SLO (p95 < 500 ms) |
| `overlook_ingestion_runs_total{source,status}` | Sync success, failure and skips per provider |
| `overlook_ingestion_records_total{source,outcome}` | Inserted, updated, unchanged and rejected volume |
| `overlook_provider_circuit_state{source}` | 0 closed · 1 half-open · 2 open |
| `overlook_sse_clients` | Live stream subscribers |

**Alerts** (`deploy/prometheus/alerts.yml`): 5xx ratio > 2 % for 10 min, p95 > 500 ms, a circuit open for 15 min, and no ingestion runs for 30 min (no leader).

The Grafana dashboard "OverLook — Service Overview" is provisioned automatically under the observability profile.

## 6. Runbook

| Symptom | Check | Action |
|---|---|---|
| Map not updating | `overlook_ingestion_runs_total` flat; worker logs for `acquired ingestion leadership` | Restart the worker. If no replica gains leadership, check DB connectivity from the worker. |
| One layer empty or stale | `/api/v1/sources/{id}` → `status`, `lastErrorMessage`; `/runs` | Provider outage or rate limit: the breaker retries on its own. Confirm upstream status. |
| `/health/ready` is 503 | DB reachable? Migrations applied? | Run the `migrate` job, then check credentials and network. |
| Many 429s | `overlook_http_rate_limited_total`; is `TRUSTED_PROXY_COUNT` right? | A wrong proxy count makes every client share one bucket. |
| Browser shows "POLLING" | `/api/v1/stream` through the proxy | The proxy must not buffer it. See `location /api/v1/stream` in `frontend/nginx.conf`. |

## 7. Local development without Docker

```bash
make install && make api    # :8000, in-memory store, embedded scheduler
make web                    # :5173
```
