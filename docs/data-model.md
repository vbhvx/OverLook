# Normalized Signal Data Model & Database Schema

## Common Signal Envelope (`signals`)

Every heterogeneous signal category is transformed into the canonical `SignalEnvelope` before persistence and API transmission:

```json
{
  "id": "eq-hv75069057",
  "sourceId": "usgs-earthquakes",
  "sourceRecordId": "hv75069057",
  "category": "earthquake",
  "signalType": "seismic-event",
  "geometry": {
    "type": "Point",
    "coordinates": [-155.367, 19.021, 28.6]
  },
  "latitude": 19.021,
  "longitude": -155.367,
  "altitudeM": -28600.0,
  "observedAt": "2026-11-10T11:15:13.640Z",
  "publishedAt": "2026-11-10T11:18:22.000Z",
  "ingestedAt": "2026-11-10T11:19:01.120Z",
  "validFrom": null,
  "validUntil": null,
  "dataStatus": "actual",
  "isSimulated": false,
  "sourceUrl": "https://earthquake.usgs.gov/earthquakes/eventpage/hv75069057",
  "source": {
    "id": "usgs-earthquakes",
    "name": "USGS Earthquake Hazards Program",
    "attribution": "Data courtesy of the U.S. Geological Survey (USGS)"
  },
  "metadata": {
    "magnitude": 2.2,
    "depthKm": 28.6,
    "place": "22 km ESE of Naalehu, Hawaii",
    "reviewStatus": "automatic",
    "tsunamiWarning": false
  },
  "rawRecordHash": "8f48c10928a6f43e01bc...",
  "schemaVersion": "1.0.0",
  "lastSeenAt": "2026-11-10T11:19:01.120Z"
}
```

## Database Schema (PostGIS)

The schema is owned by Alembic (`backend/migrations/versions/`). There are three tables:

| Table | Purpose | Key indexes |
|---|---|---|
| `signals` | One row per normalized signal. `payload` (JSONB) holds the full envelope above. The remaining columns exist to filter, sort and index on. | `GIST(geom)`, `GIST(point)`, `(observed_at DESC, id)`, `(category, observed_at DESC)`, `(source_id)`, partial `(last_seen_at) WHERE NOT is_simulated` |
| `source_state` | Runtime health per provider (status, last success or error, consecutive failures, circuit state), written by the worker and read by every API replica. | PK `source_id` |
| `sync_runs` | Audit log of every sync: counts fetched, inserted, updated and rejected, plus duration and error. Pruned after 7 days. | `(source_id, started_at DESC)` |

`geom` is `geometry(Geometry, 4326)` holding the true footprint (points, or satellite swath polygons), forced to 2-D. `point` is `geography(Point, 4326)` at the representative position, used for metre-accurate `ST_DWithin` radius search. `CHECK` constraints pin `category` and `data_status` to the enum values. See [ADR 0002](adr/0002-jsonb-payload-with-indexed-columns.md) for the rationale.

### Ingestion semantics

| Incoming record | Effect |
|---|---|
| New `id` | Inserted |
| Known `id`, different `rawRecordHash` | Payload replaced, original `ingestedAt` kept, `lastSeenAt` bumped (for example, a USGS magnitude revision) |
| Known `id`, same hash | Only `lastSeenAt` bumped |
| `observedAt` more than 10 min in the future (non-forecast), naive timestamp, or `validUntil < validFrom` | Rejected and counted in `recordsRejected` |

**Retention:** live signals not seen for `SIGNAL_RETENTION_HOURS` (default 72) are deleted every 10 minutes. Simulated fixtures are never pruned.

Correlations (`SignalRelation`, `InvestigationEvent`) are derived at query time from the rules in `backend/app/correlation/engine.py`. They are not stored, so they always reflect current data and the current rule version.
