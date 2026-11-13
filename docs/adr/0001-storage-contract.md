# 0001 — One storage contract, two engines, one test suite

## Context
The API, correlation engine and ingestion pipeline all need spatial and temporal queries. The original code kept signals in a module-level dict and scanned it linearly; the PostGIS schema existed but was never read or written. We need durable storage in production without making every developer and every unit test depend on a running database.

## Decision
Define `SignalStore` (`backend/app/storage/base.py`) as the only way to read or write signals and ingestion bookkeeping. Ship two implementations:

- `InMemorySignalStore` — linear scans, atomic per call because it never awaits.
- `PostGISSignalStore` — GiST-indexed geometry and geography, `date_bin` timelines, transactional upserts.

`tests/test_store_contract.py` runs the same 17 behavioural tests against every implementation. PostGIS runs whenever `OVERLOOK_TEST_DATABASE_URL` is set, and CI always sets it.

## Consequences
- Unit tests and local development need no database; CI still proves the two engines behave the same.
- Semantics must be defined precisely enough to test: ordering ties break on `id`, bucket edges align to `start`, and the antimeridian is handled.
- A small known divergence: memory distances are haversine (sphere), PostGIS distances are geodesic (spheroid). They agree to well under 1%, and the contract asserts with a 5% tolerance.
- The memory store is not meant for large datasets. That is a documented boundary, not a hidden one.
