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
  "version": "1.0.0",
  "environment": "development",
  "activeSignals": 142,
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
Triggers an immediate synchronization run for a provider adapter.

### 4. `GET /api/v1/layers`
Returns available map layers, geometry types, refresh intervals, and active signal counts.

### 5. `GET /api/v1/signals`
Queries signals with multi-parameter filtering:
- `bbox`: `west,south,east,north` (e.g. `-123.5,37.0,-121.5,38.5`)
- `category`: `earthquake`, `weather`, `aircraft`, `vessel`, `satellite`, `camera`, `infrastructure`
- `source`: Provider identifier
- `data_status`: `actual`, `forecast`, `stale`, `delayed`, `simulated`
- `start`: ISO 8601 UTC timestamp
- `end`: ISO 8601 UTC timestamp
- `limit`: Integer (1 - 1000, default 250)
- `offset`: Pagination offset

### 6. `GET /api/v1/signals/{signal_id}`
Retrieves complete signal envelope, SHA-256 fingerprint, source link, and nearby correlated signals within 60km.

### 7. `GET /api/v1/timeline`
Returns histogram frequencies of observations bucketed by time interval.
- Query parameters: `hours` (1 - 168), `interval_hours` (1 - 24), `category`

### 8. `GET /api/v1/events`
Returns synthesized multi-source correlation events (e.g. seismic activity + surrounding infrastructure/weather, multimodal transit corridor).

### 9. `GET /api/v1/regions`
Returns predefined analytical hotspots (San Francisco Bay, Hawaii, Mediterranean, English Channel, Tokyo Bay, Strait of Malacca).

### 10. `GET /api/v1/map/summary`
Returns global counts, category breakdowns, and status distribution.

