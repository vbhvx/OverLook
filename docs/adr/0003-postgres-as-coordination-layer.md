# 0003 — Postgres for leader election and event fan-out

## Context
Ingestion must run exactly once even with several worker replicas, because providers enforce daily request budgets. API replicas must learn when new data lands so they can notify browsers. Common answers are Redis (locks and pub/sub), Kafka, or a managed scheduler.

## Decision
Use the database we already operate:

- **Leader election:** each worker calls `pg_try_advisory_lock` on a dedicated session. The holder ingests; others poll every 10 s. If the leader dies, Postgres ends its session and releases the lock.
- **Fan-out:** after a sync that changed data, the worker calls `pg_notify('overlook_events', …)`. Every API replica holds one `LISTEN` connection and relays events to its SSE subscribers.

## Consequences
- No new infrastructure. Failure detection is the database's own session liveness, so there are no lease timers to tune.
- Events are *hints* ("source X changed"), not data, and are delivered at most once. A missed event costs one stale view until the next event or the fallback poll, which is acceptable for a map. Anything needing guaranteed delivery would need an outbox table.
- `NOTIFY` payloads are capped at 8 KB. Ours are a few hundred bytes.
- Each process holds one or two extra connections, which must be counted against `max_connections` when sizing.
- If ingestion ever needs partitioning across workers (for example, one leader per source), the same mechanism extends to per-source lock keys.
