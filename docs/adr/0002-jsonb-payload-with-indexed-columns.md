# 0002 — Canonical JSONB payload plus indexed query columns

## Context
Signals from seven categories share an envelope but carry very different metadata (magnitude and depth; callsign and squawk; cloud cover and sensor). A fully normalized table per category would need a migration for every new provider field and would complicate cross-category queries.

## Decision
Each `signals` row stores the complete `SignalEnvelope` as `payload JSONB`, plus the columns we filter, sort or index on: `category`, `data_status`, `source_id`, `observed_at`, `last_seen_at`, `is_simulated`, `raw_record_hash`, `geom` (geometry) and `point` (geography). Reads rehydrate from `payload`.

## Consequences
- Adding a metadata field needs no migration. Making a field *queryable* does, and that is the trade we want.
- Indexed columns and the payload must stay consistent. Both are written in the same statement from the same envelope (`_row_params`).
- `geom` keeps true footprints (satellite swaths are polygons) for bbox intersection. `point` is the representative position for metre-accurate radius search. Altitude and depth are dropped from the indexed geometry (`ST_Force2D`) but kept in the payload.
- Retention uses a partial index (`WHERE NOT is_simulated`), so the sweep only touches live data.
