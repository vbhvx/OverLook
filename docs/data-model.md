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

## Relational Entity Schema

1. **`sources`**: Provider registration, capabilities, license contracts, last sync timestamps, error states.
2. **`source_sync_runs`**: Audit log of sync executions, records fetched, records updated, duration, and error codes.
3. **`source_records`**: Raw provider records, external IDs, and SHA-256 fingerprints preventing duplicate signals.
4. **`signals`**: Primary table containing normalized spatial geometries, timestamps, status, and domain metadata.
5. **`signal_relations`**: Explicit spatial-temporal linkages between signals with distance (km), time delta (s), rule name, and methodological disclaimers.
6. **`saved_regions`**: Preset and user-defined geographic boundaries (SF Bay, Mediterranean, English Channel, Malacca Strait, Hawaii, Tokyo Bay).

