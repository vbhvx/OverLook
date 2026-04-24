# Technical Specification: Public Signal Intelligence & Situational Awareness Platform

**Project type:** Full-stack geospatial engineering challenge  
**Product category:** OSINT · Geospatial Intelligence · Real-Time Data Integration  
**Initial scope:** Global map with configurable geographic regions and multiple public-signal layers  
**Data categories:** Aircraft · Ships · Satellites · Earthquakes · Weather · Public Cameras · Infrastructure  
**Architecture:** React + TypeScript · Python + FastAPI · PostgreSQL + PostGIS · MapLibre GL JS  
**Delivery approach:** Phased implementation with verifiable data, source-aware visualization, and explicit integration boundaries

## Objective

Build a responsive geospatial intelligence application that consolidates public, authorized, and appropriately licensed real-world signals into a unified interactive map.

The application should help users understand what is happening in a geographic area by exploring multiple independent layers, examining the original evidence, reviewing timelines, and understanding relationships between signals.

Instead of switching between separate aircraft trackers, ship trackers, satellite dashboards, earthquake feeds, weather services, public camera directories, and infrastructure maps, users should have one coherent workspace for exploring these sources.

The platform must not merely place unrelated datasets on the same map. It should normalize their spatial and temporal information, communicate their provenance and freshness, preserve the differences between data types, and help users investigate potentially related events without presenting speculation as established fact.

**Priority order:** source verification → data correctness → spatial and temporal normalization → trustworthy multi-layer visualization → useful cross-source exploration → event correlation → responsive performance → testing → deployment.

The result should be an analytical situational-awareness platform, not a system for targeting individuals, enabling unauthorized surveillance, or making unsupported claims about real-world events.

---

## 1. Scope and acceptance criteria

### Required for the initial release

- Responsive web application with an interactive geospatial map.
- Multiple selectable signal layers.
- Unified search by geographic area, time, category, and supported entity or event.
- Source-aware signal detail panels.
- A timeline for navigating signals by observation time.
- Normalized geospatial data using a documented internal schema.
- Source registry containing provider metadata and capability status.
- Source timestamps, ingestion timestamps, freshness indicators, and attribution.
- Clearly labeled simulated data for development and demonstrations.
- At least two verified real-data integrations chosen after source inspection.
- Automated tests for parsing, normalization, time handling, geometry, and API behavior.
- Appropriate database persistence and indexes.
- Docker-based local setup where practical.
- README with setup instructions, source documentation, assumptions, and limitations.
- Deployment instructions and a verifiable release checklist.

### Required signal categories

The data architecture must accommodate all seven requested categories.

| Category | Examples of supported information | Important limitations |
|---|---|---|
| Aircraft | Publicly available aircraft position reports and supported flight metadata | Coverage, delays, identifiers, and commercial-use restrictions vary by provider |
| Ships | Authorized AIS-derived vessel positions and available public vessel metadata | Coverage and availability vary; public web visibility does not guarantee API access |
| Satellites | Public orbital data and authorized Earth-observation catalog metadata | Orbit estimates, observation times, and image-acquisition times are different concepts |
| Earthquakes | Event locations, origin times, magnitudes, depths, and source updates | Events and their reported parameters may be revised |
| Weather | Conditions, forecasts, alerts, and observation metadata | Forecasts are estimates; stations and models have different coverage and update intervals |
| Public cameras | Metadata and links for explicitly public, authorized camera feeds | No unauthorized CCTV access, private feeds, or unapproved video scraping |
| Infrastructure | Public geographic features, transport networks, landmarks, and appropriately licensed open datasets | Do not expose sensitive operational details or create vulnerability-targeting workflows |

The initial release does not need every category to have a production-ready live integration. It does need a working source registry, a reusable adapter architecture, realistic simulated fixtures, and a clear status for every integration.

### Required analytical correctness

- Normalize geographic coordinates and validate geometry.
- Normalize timestamps into UTC while preserving source time and timezone metadata.
- Distinguish observation time, publication time, ingestion time, and valid time.
- Preserve source identifiers and original source links.
- Prevent duplicate ingestion from producing duplicate signals.
- Keep missing data separate from genuine zero values.
- Identify stale, delayed, unavailable, and simulated information.
- Avoid joining records solely because they are geographically close.
- Present cross-source correlations as hypotheses unless supported by sufficient evidence.
- Display coverage limitations and provider failures.
- Never manufacture real-time updates, locations, source records, or incident explanations.

### Explicitly out of scope for the initial MVP

- Accessing private camera systems or circumventing authentication.
- Face recognition or identification of people in public footage.
- Building dossiers on private individuals or inferring their routines.
- Unauthorized tracking or surveillance of a specific individual.
- Tactical targeting, target selection, or operational tracking for violent purposes.
- Identifying exploitable weaknesses in sensitive infrastructure.
- Unauthorized redistribution of commercial datasets.
- Automatic claims that an aircraft, vessel, satellite, or infrastructure feature is associated with a particular incident without supporting evidence.
- Autonomous emergency response or control of physical infrastructure.
- Guaranteed real-time coverage of all categories.
- Machine-learning models trained on unverified or improperly licensed data.

The application is an analytical information system. It must communicate uncertainty and the limitations of public data rather than claiming comprehensive real-world visibility.

---

## 2. Data-source specification

Treat every data source as a separate integration with its own contract, limitations, and usage permissions.

### 2.1 Aircraft signals

Potential data includes aircraft state vectors, position, altitude, heading, velocity, observation time, and available flight metadata.

A candidate source is the [OpenSky Network REST API](https://openskynetwork.github.io/opensky-api/rest.html).

Before integration, verify:

- Authentication requirements.
- Available endpoints and response schema.
- Geographic query restrictions.
- Historical-data availability.
- API credits and rate limits.
- Position and observation-time semantics.
- Field availability and missing-value behavior.
- Commercial-use permission and attribution requirements.

OpenSky documents rate limits and requires consent for commercial use. Do not assume a public account is sufficient for a commercial or production deployment.

Normalize available data into the common signal schema. Do not invent an aircraft registration, destination, operator, or flight route when the source does not provide it.

### 2.2 Ship and vessel signals

Use an explicitly selected maritime data provider whose API access and usage rights have been confirmed.

Potential signal attributes include:

- Provider vessel identifier.
- Position.
- Course and speed, when reported.
- Observation time.
- Available vessel class or metadata.
- Source freshness.
- Original record reference.

Verify:

- Geographic coverage.
- Position update frequency.
- Historical access.
- Subscription requirements.
- Commercial licensing and redistribution rights.
- API response and error contracts.
- Available identifiers and their reliability.

Do not build against undocumented endpoints or scrape a commercial vessel-tracking website to imitate an authorized API.

Missing vessel identity must remain missing. A location report alone is not proof of a vessel's ownership, mission, cargo, or intent.

### 2.3 Satellite and Earth-observation signals

Support two distinct concepts:

**Orbital information:** Publicly available orbital elements or position estimates from verified sources, where permitted.

**Earth observation:** Catalog metadata for satellite imagery, including acquisition time, geographic footprint, sensor, processing level, and authorized imagery access links.

These are not interchangeable. A satellite's calculated position does not mean it captured an image of the point beneath it at that exact time.

A candidate for Earth-observation data is the [Copernicus Data Space Ecosystem API documentation](https://documentation.dataspace.copernicus.eu/APIs.html).

Verify:

- Dataset and product coverage.
- Authentication and access requirements.
- Geographic and temporal query capabilities.
- Data licensing and permitted reuse.
- Image-download restrictions and processing requirements.
- Orbital element source, epoch, and validity limitations.
- Catalog timestamps versus actual acquisition timestamps.

For the initial MVP, catalog metadata and authorized links may be sufficient. Do not download or process large raster datasets unless the implementation requires it.

### 2.4 Earthquake signals

Use an established earthquake catalog with documented event identifiers and update semantics.

A candidate source is the [USGS Earthquake Catalog API](https://earthquake.usgs.gov/fdsnws/event/1/).

The source can support event queries in GeoJSON, including spatial and temporal filtering.

Potential normalized attributes include:

- Event identifier.
- Latitude and longitude.
- Origin time.
- Magnitude and magnitude type.
- Depth.
- Place description, when provided.
- Event URL.
- Source update time.
- Status or revision metadata, when available.

Handle revised, superseded, and removed events where the source exposes these states.

Do not assume the first reported location or magnitude is immutable. Preserve updates and distinguish the original observation from the currently preferred source record.

### 2.5 Weather signals

Choose a documented provider that covers the required geographic regions and data types.

Potential information includes:

- Observed conditions.
- Forecast conditions.
- Temperature and precipitation.
- Wind speed and direction.
- Severe-weather alerts.
- Observation stations and measurement metadata.
- Forecast issue time and validity interval.

A potential candidate is [Open-Meteo](https://open-meteo.com/), subject to the actual usage terms and the selected deployment model. Its published terms distinguish non-commercial access from commercial use.

Verify:

- Geographic coverage.
- Provider and model identity.
- Forecast versus observation semantics.
- Forecast initialization time.
- Observation time and forecast validity period.
- Units and conversions.
- Update intervals and request limits.
- Commercial-use, attribution, and caching conditions.

Never label a forecast as a confirmed observation. If a forecast predicts a storm, show it as a forecast with its valid interval and source, not as evidence that the storm has already occurred.

### 2.6 Public camera signals

Support only camera metadata and feeds that are explicitly public and authorized for the intended use.

Possible fields include:

- Camera identifier.
- Display name.
- Public location.
- Source organization.
- Feed or webpage URL.
- Feed type.
- Last-verified timestamp.
- Availability state.
- License and access restrictions.

For the initial release, camera metadata and links to original publishers may be sufficient.

Do not crawl the internet for exposed camera credentials, bypass access controls, access private CCTV, or use unsupported URLs that reveal private video streams.

Do not implement facial recognition, biometric identification, or identity inference. Avoid retaining video frames by default.

When an embedded feed is permitted, validate the source, content security policy, and embedding terms. Prefer linking to the original source if embedding is prohibited or unreliable.

### 2.7 Infrastructure and geographic context

Use authorized open geographic data or data from verified public-sector providers.

Suitable initial layers may include:

- Administrative boundaries.
- Roads and transport networks.
- Public landmarks and facilities.
- Publicly documented geographic features.
- Publicly available infrastructure categories where reuse is authorized.

A potential base-map and geographic-data source is [OpenStreetMap](https://www.openstreetmap.org/). Its data licensing, tile-service terms, and geocoding-service policy must be treated separately.

Relevant official policies include:

- [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
- [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).

Do not assume that the availability of open map data grants unlimited use of OpenStreetMap's hosted tile or geocoding infrastructure.

Use infrastructure data to provide ordinary geographic context. Do not create functions that expose non-public access points, security weaknesses, or sensitive operational details.

### 2.8 First task: verify source contracts before map integration

Before building the full dashboard:

1. Select a small representative subset of providers.
2. Inspect official documentation and permitted use.
3. Retrieve a small number of representative responses.
4. Confirm the actual schema, units, coordinate reference system, and timestamps.
5. Check missing fields, duplicate records, revisions, and pagination.
6. Measure request limits and expected update intervals.
7. Determine which data can be stored, cached, displayed, or redistributed.
8. Document attribution requirements.
9. Implement a test parser for each selected provider.
10. Add source health and disabled states.

**Stop condition:** Do not build the complete real-data visualization around an assumed API contract. First verify that the source can supply the actual fields needed by the UI under the intended usage terms.

---

## 3. Architecture and technology choices

Use a geospatially capable modular architecture. Keep the first implementation small enough to test and explain.

| Component | Recommended choice | Reason |
|---|---|---|
| Frontend | React, TypeScript, Vite | Fast iteration and clear component structure |
| Interactive map | MapLibre GL JS | Layered vector and raster map visualization |
| Frontend styling | Tailwind CSS or equivalent | Consistent layout and responsive design |
| Backend | Python + FastAPI | Typed APIs and geospatial data processing |
| HTTP client | `httpx` | Timeouts, connection pooling, and request handling |
| Data validation | Pydantic | Runtime validation of API and normalized records |
| Geospatial processing | GeoPandas/Shapely where justified | Geometry validation and transformations |
| Database | PostgreSQL + PostGIS | Spatial queries, indexing, and persistence |
| Data analysis | Pandas where useful | Normalization and aggregation |
| Background processing | Worker and queue when required | Scheduled source synchronization |
| Cache | Redis or a suitable TTL cache | Reduce provider load and improve repeated queries |
| Charts and timelines | Recharts or a suitable visualization library | Counts, temporal trends, and source health |
| Testing | pytest and Vitest | Backend and frontend behavior |
| Browser automation | Playwright | End-to-end interaction testing |
| Containerization | Docker Compose | Reproducible local setup |
| Mapping base layer | Verified tile or vector-tile provider | Geographic context and attribution |
| Deployment | Web frontend and Docker-capable API/database hosting | Independent deployment and operational control |

### Architecture diagram

```text
Public / Authorized Data Sources
    ├── Aircraft
    ├── Vessels
    ├── Satellite / Earth Observation
    ├── Earthquakes
    ├── Weather
    ├── Public Cameras
    └── Infrastructure
               |
               v
      Provider Adapters
               |
               v
   Validation + Normalization
               |
               v
      PostgreSQL + PostGIS
               |
               v
     Query / Correlation API
               |
       ┌───────┴────────┐
       v                v
   Map Layers        Timeline /
   and Filters       Event Detail
       └───────┬────────┘
               v
        React Dashboard
```

Use a backend cache or background worker only when justified by provider limits, request volume, or synchronization requirements.

Do not fetch every source directly from the browser. Centralizing provider access makes it easier to validate records, control rate limits, protect credentials, enforce licensing restrictions, and report source health.

### Core architectural rule

The map is a presentation layer, not the source of truth.

Provider adapters establish what data was received. The normalization layer validates its meaning. The database stores queryable records and provenance. The API returns signals with clear temporal and spatial semantics. The frontend renders the resulting data without inventing new facts.

---

## 4. Core business logic

This is the most important part of the application.

### 4.1 Normalize heterogeneous signals

Every provider will use different naming conventions, timestamps, identifiers, coordinates, and metadata.

Define a common envelope for all signal categories.

A normalized signal should contain fields equivalent to:

| Field | Meaning |
|---|---|
| `id` | Internal unique identifier |
| `source_id` | Registered provider identifier |
| `source_record_id` | Original provider record identifier, where available |
| `category` | Aircraft, vessel, satellite, earthquake, weather, camera, or infrastructure |
| `signal_type` | More specific record type |
| `geometry` | Validated spatial geometry |
| `observed_at` | Time the source says the observation occurred |
| `published_at` | Time the source published the record, if known |
| `ingested_at` | Time the application received the record |
| `valid_from` | Start of the record's validity interval, if applicable |
| `valid_until` | End of the record's validity interval, if applicable |
| `source_url` | Original record or source page |
| `data_status` | Actual, forecast, stale, delayed, simulated, or other supported state |
| `source_metadata` | Category-specific normalized fields |
| `raw_record_hash` | Fingerprint for duplicate detection |
| `schema_version` | Normalized contract version |

Use a versioned schema so provider changes can be introduced deliberately.

Do not force unrelated categories into the same specific attributes. A weather forecast, an earthquake event, and an aircraft position should share the common envelope while retaining their own typed metadata.

### 4.2 Spatial normalization

Use a consistent internal coordinate reference system, normally WGS84 for geographic point and map data.

Validate:

- Latitude and longitude ranges.
- Geometry type.
- Coordinate order.
- Missing coordinates.
- Invalid or empty geometry.
- Geometry collections, polygons, and bounding boxes.
- Antimeridian-crossing areas.
- Spatial reference metadata supplied by the source.

Remember that longitude and latitude can be accidentally reversed. Test this explicitly.

Use spatial indexes such as PostGIS GiST indexes for geographic search.

Do not assume every source point is accurate to the displayed decimal precision. Where accuracy metadata is available, preserve it. Avoid communicating false precision through map markers or tooltips.

### 4.3 Temporal normalization

Normalize timestamps to UTC for internal comparisons and storage.

Preserve the original timestamp and its interpretation from the provider.

Distinguish:

- Event or observation time.
- Provider publication time.
- Ingestion time.
- Forecast issue time.
- Forecast validity interval.
- Satellite image acquisition time.
- Satellite orbital-element epoch.

Do not use ingestion time as a substitute for observation time.

Handle records that arrive late, are revised, have missing timestamps, or refer to an earlier period.

A time filter must use the appropriate timestamp semantics for each category. If a category provides only an approximate time, make that limitation visible.

### 4.4 Duplicate detection and source updates

Implement deterministic deduplication.

Prefer provider identifiers when stable and documented. Otherwise use a composite key based on the source, category, record attributes, observation time, and a normalized record fingerprint.

A revised earthquake magnitude or corrected source record should not automatically create a completely unrelated event when the source provides a stable identity.

Handle:

- Repeated polling results.
- Duplicate webhook or feed deliveries.
- Updated source records.
- Late-arriving observations.
- Deleted or superseded source events, where supported.
- Schema changes.

Record when a source record was last seen and last changed.

Do not permanently discard history where version changes are important for event interpretation.

### 4.5 Geographic and temporal filtering

Support queries by:

- Geographic bounding box.
- Selected map area.
- Time range.
- Signal category.
- Source.
- Data status.
- Supported event attributes.
- Provider freshness.

Apply filtering on the backend when it materially reduces the data returned to the browser.

Use appropriate spatial and time indexes. Bound result sizes, use cursor pagination where needed, and avoid sending an entire global dataset to the frontend.

For dynamic signals, prefer viewport-bounded queries or appropriately aggregated data. For map zoomed far out, cluster or aggregate records rather than rendering an unbounded number of individual markers.

### 4.6 Multi-layer map logic

Allow users to enable and disable signal layers independently.

Each layer must define:

- Supported category.
- Required fields.
- Marker or geometry type.
- Styling rules.
- Refresh policy.
- Visibility at different zoom levels.
- Loading and failure state.
- Attribution.
- Data freshness behavior.

Use distinct and accessible visual encodings for different categories. Do not use color alone to communicate critical status.

Avoid visually implying that two signals are related merely because they share a color or appear close together.

The frontend should remain usable when one data provider fails. A failure in weather data must not hide earthquake or infrastructure data.

### 4.7 Cross-source event correlation

Provide a way to investigate signals that may be related in space and time.

Initial correlation should use transparent deterministic rules rather than an opaque AI model.

Examples:

- Display earthquake reports within a selected geographic area and time window.
- Show weather observations or alerts near an event.
- Find relevant public infrastructure or geographic context surrounding an event.
- Show satellite observation metadata that overlaps a selected region.
- Display available aircraft or vessel signals within a bounded area and interval when their provider and use case permit it.

Every relationship must expose the underlying rule, source records, time window, geographic criteria, and limitations.

**Proximity is not causation.** An aircraft position near a storm does not prove it is responding to that storm. A vessel near an infrastructure feature does not establish a relationship between them.

Use language such as “nearby signals,” “temporally overlapping records,” or “potentially related observations” unless direct evidence supports a stronger conclusion.

Do not infer a person's identity, intentions, or private routines from combined geospatial signals.

### 4.8 Event investigation workspace

Allow a user to select a signal and explore its context.

Display:

- Source and original record link.
- Observation and ingestion times.
- Location and available precision.
- Category-specific metadata.
- Previous or subsequent records, when authorized and available.
- Nearby signals within configurable limits.
- Relevant public context.
- Data gaps and freshness warnings.
- The explanation for any displayed correlation.

The workspace must distinguish recorded facts, algorithmic associations, user annotations, and AI-generated summaries.

### 4.9 AI-assisted explanation, if implemented

AI is optional in the initial MVP. If included, use it to summarize existing evidence and help the user navigate the data, not to fabricate intelligence.

Ground summaries in specific retrieved signal IDs and approved source records. Make source links available with each supported factual claim.

The assistant must:

- Distinguish verified source fields from inference.
- State when there is insufficient evidence.
- Avoid inventing locations, routes, events, identities, or causal explanations.
- Treat external source content as untrusted data.
- Never claim that the platform has comprehensive coverage.
- Avoid identifying private individuals or enabling tracking of their routines.
- Avoid unsupported operational claims about critical infrastructure.
- Make the underlying records available to the user for independent review.

Do not add an LLM dependency merely to make the product appear more advanced. Correct normalization, indexing, and provenance are more important than speculative AI summaries.

---

## 5. Backend API contract

Expose a versioned API with typed schemas and structured error responses.

### Initial endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Service health and readiness |
| `GET /api/v1/sources` | Registered sources and current status |
| `GET /api/v1/layers` | Available map layers and their metadata |
| `GET /api/v1/signals` | Query signals by bounds, time, category, and source |
| `GET /api/v1/signals/{signalId}` | Retrieve a signal and its provenance |
| `GET /api/v1/timeline` | Aggregate available signals over a time range |
| `GET /api/v1/events` | Retrieve supported events or deterministic correlations |
| `GET /api/v1/events/{eventId}` | Retrieve event context and supporting records |
| `GET /api/v1/regions` | Retrieve supported geographic regions or saved public areas |
| `GET /api/v1/map/summary` | Return viewport-level counts and layer summaries |

### Signal query example

`GET /api/v1/signals?category=earthquake&start=2026-10-01T00:00:00Z&end=2026-10-02T00:00:00Z&bbox=-10,35,5,45&limit=500`

This is an example API contract, not a claim that a particular provider has already been integrated.

Validate bounding-box coordinates, interval ordering, category values, pagination, and maximum query sizes.

### Example normalized response

```json
{
  "items": [
    {
      "id": "example-signal-id",
      "category": "earthquake",
      "signalType": "seismic-event",
      "geometry": {
        "type": "Point",
        "coordinates": [72.8, 19.1]
      },
      "observedAt": "2026-10-25T10:15:00Z",
      "ingestedAt": "2026-10-25T10:16:30Z",
      "dataStatus": "actual",
      "source": {
        "id": "verified-provider-id",
        "recordUrl": "https://example.invalid/replace-with-verified-record-url"
      },
      "metadata": {
        "magnitude": null,
        "depthKm": null
      }
    }
  ],
  "meta": {
    "limit": 500,
    "nextCursor": null,
    "partial": false
  }
}
```

This response is a **schema illustration using placeholder data**, not a real earthquake record. Replace all example identifiers, URLs, and values with verified data before presenting it as actual information.

### Additional provider endpoints

Provider-specific ingestion and synchronization routes should remain internal unless there is an explicit reason to expose them.

For external callbacks or webhooks, validate the sender, signature where available, event identifier, timestamp, and idempotency behavior.

Do not create an unrestricted API endpoint that lets a client supply an arbitrary URL for the server to fetch. Use configured provider adapters to avoid SSRF and untrusted network access.

### API requirements

- Validate requests and responses at runtime.
- Use consistent response schemas.
- Include request IDs for diagnostics.
- Apply rate limits and bounded query sizes.
- Return explicit freshness, partial-data, and provider-error states.
- Reject invalid geometry and timestamps.
- Do not expose provider secrets or internal stack traces.
- Use appropriate HTTP status codes: `400` for malformed requests, `422` for semantically invalid input where appropriate, `502` or `503` for upstream failures, and `429` for rate limiting.
- Keep provider-specific data normalization in the backend.

---

## 6. Frontend specification

Build a single responsive geospatial intelligence workspace with five principal sections.

### A. Global map

Display the base map and selectable signal layers.

Required functionality:

- Pan and zoom.
- Category layer toggles.
- Bounding-box-based queries.
- Clustered markers at lower zoom levels.
- Detail markers at higher zoom levels.
- Loading and empty states.
- Source-specific error indicators.
- Layer legend.
- Map attribution.
- Clear indication of stale or simulated content.

Only render data within the supported query extent and time window.

### B. Layer control panel

Allow users to enable, disable, and configure supported categories:

- Aircraft.
- Ships.
- Satellites.
- Earthquakes.
- Weather.
- Public cameras.
- Infrastructure.

For each layer, show its source, status, last successful update, update behavior, and relevant limitations.

If an integration is unavailable, show “Not configured,” “Awaiting authorization,” or another precise status instead of pretending that it is live.

### C. Timeline and filters

Provide a timeline or time-range selector with:

- Start and end time.
- Timezone clarity.
- Category filters.
- Source filters.
- Optional event-specific filters.
- Signal counts.
- Available-data coverage.
- Playback of stored historical records where history exists.

A playback animation must replay stored timestamps; it must not imply that historical records are live.

Do not interpolate missing observations in a way that makes the displayed positions look real.

### D. Signal detail panel

When a user selects a marker or event, display:

- Category and record type.
- Source and source link.
- Observation, publication, and ingestion times where available.
- Location and available accuracy information.
- Category-specific metadata.
- Data status and freshness.
- Available historical context.
- Nearby records and applicable correlation explanations.

Hide unavailable fields rather than displaying invented placeholders as facts.

### E. Event investigation panel

Allow users to inspect a region or selected event and review potentially related signals.

Include:

- Selected geographic area.
- Relevant time interval.
- Supporting source records.
- Source timestamps and freshness.
- Correlation rule and matching criteria.
- Contradictory or missing evidence where known.
- Public geographic context.

Do not automatically turn a cluster of records into a definitive narrative.

### General UI requirements

- Responsive layouts for desktop and mobile.
- Clear typography and accessible color contrasts.
- Keyboard-accessible controls.
- Accessible alternatives to map-only information.
- Loading, empty, error, stale, partial, and offline states.
- Debounced search and bounded map queries.
- No unbounded polling or repeated requests during map dragging.
- Explicit demo-mode labeling.
- Clear separation between recorded facts and derived associations.
- Visible attribution for map and data providers.

The map should be useful without being visually overwhelming. Users must be able to disable layers independently and understand the selected signal without needing to inspect every layer.

---

## 7. Database schema

Use PostgreSQL with PostGIS for persistent geospatial data.

The schema should preserve source records, normalized attributes, time semantics, and enough history to explain how the displayed result was obtained.

### Required tables

| Table | Purpose |
|---|---|
| `sources` | Provider registry, capabilities, license state, and configuration metadata |
| `source_sync_runs` | Ingestion history, timings, record counts, and failures |
| `source_records` | Provider identifiers, source timestamps, version metadata, and record fingerprints |
| `signals` | Common normalized signal attributes and provenance |
| `signal_positions` | Position observations for sources that produce time-series locations |
| `signal_events` | Events and updated or revised event states |
| `signal_relations` | Explicit associations between signals and the rules supporting them |
| `map_layers` | Layer definitions, configuration, and display metadata |
| `saved_regions` | Named geographic areas saved by the user, where accounts are enabled |
| `saved_views` | Layer, time, and filter preferences, where persistence is required |
| `audit_events` | Important administrative and security actions |
| `data_quality_events` | Invalid records, stale data, schema changes, and reconciliation findings |

### `sources`

Suggested fields:

`id`, `name`, `category`, `provider_type`, `official_docs_url`, `status`, `license_status`, `commercial_use_status`, `attribution_requirements`, `supported_capabilities`, `refresh_policy`, `rate_limit_policy`, `last_success_at`, `last_error_at`, `disabled_reason`, `created_at`, `updated_at`.

Do not activate a production source just because its name and endpoint have been configured.

### `source_records`

Suggested fields:

`id`, `source_id`, `external_record_id`, `record_hash`, `source_published_at`, `source_observed_at`, `source_updated_at`, `source_version`, `raw_payload_reference`, `ingested_at`, `processing_status`, `validation_errors`.

Raw payloads should be retained only when useful, permitted, and consistent with the retention policy. Otherwise, retain a suitable normalized record and diagnostic fingerprint.

### `signals`

Suggested fields:

`id`, `source_record_id`, `category`, `signal_type`, `geometry`, `observed_at`, `published_at`, `ingested_at`, `valid_from`, `valid_until`, `data_status`, `source_url`, `metadata`, `schema_version`, `is_simulated`, `created_at`, `updated_at`.

Use PostGIS geometry types suitable for the category, with appropriate spatial reference definitions.

### `signal_positions`

For sources that produce position time series:

`id`, `signal_id`, `source_id`, `geometry`, `position_timestamp`, `ingested_at`, `position_quality`, `accuracy_metadata`, `source_record_id`.

Enforce appropriate uniqueness and deduplication constraints based on the source contract.

Do not store high-frequency position histories indefinitely by default. Define retention based on use case, source permissions, and operational needs.

### `signal_events`

Suggested fields:

`id`, `source_id`, `external_event_id`, `event_type`, `geometry`, `occurred_at`, `published_at`, `updated_at`, `status`, `metadata`, `source_url`.

Support revisions where the provider exposes them.

### `signal_relations`

Suggested fields:

`id`, `left_signal_id`, `right_signal_id`, `relation_type`, `rule_version`, `spatial_criteria`, `temporal_criteria`, `evidence_metadata`, `created_at`.

Store the reason for the association. Do not treat a proximity-based association as causal evidence.

### Database requirements

- Use geometry indexes for spatial queries.
- Use B-tree or appropriate composite indexes for timestamps, source IDs, categories, and status.
- Apply unique constraints to stable provider identifiers and deduplication keys.
- Keep ingestion records distinct from normalized signals.
- Use transactions for multi-record updates that need atomicity.
- Store timestamps consistently and preserve original source time information.
- Version the normalized schema.
- Create database migrations and documented rollback procedures.
- Implement retention and deletion rules.
- Use bounded queries and pagination.
- Never convert a missing location or timestamp to an invented value.

---

## 8. Repository structure

Keep the repository easy to navigate and review.

```text
signal-intelligence/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   ├── map/
│   │   ├── layers/
│   │   ├── timeline/
│   │   ├── events/
│   │   ├── api/
│   │   └── styles/
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── geospatial/
│   │   ├── ingestion/
│   │   ├── providers/
│   │   ├── correlation/
│   │   └── config.py
│   ├── tests/
│   │   ├── test_normalization.py
│   │   ├── test_geospatial.py
│   │   ├── test_time_handling.py
│   │   ├── test_sources.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── database/
│   ├── migrations/
│   └── seeds/
├── tests/
│   └── e2e/
├── docs/
│   ├── architecture.md
│   ├── sources.md
│   ├── data-model.md
│   ├── api.md
│   ├── data-policy.md
│   └── deployment.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Separate provider access, normalization, spatial querying, event correlation, and API routes where this makes testing easier.

Do not add microservices, multiple queues, or a complex streaming platform until measured requirements justify them.

---

## 9. Implementation checklist

Treat each phase as an independently testable milestone. Do not activate later phases until the preceding foundations are reliable.

### Phase 0 — Source verification and feasibility

- Inspect the existing repository and development environment.
- Choose the initial geographic scope and MVP data sources.
- Verify official API documentation and usage terms.
- Inspect representative responses.
- Confirm coordinate, timestamp, and identifier semantics.
- Document the source registry and data contracts.
- Define normalized signal schemas.
- Identify unavailable or commercially restricted integrations.
- Select the map and tile provider.
- Record the initial feature boundaries and known limitations.

**Gate:** The app must distinguish actual, simulated, and unavailable data before any production dashboard claims are made.

### Phase 1 — Core map and normalized data

- Set up React and TypeScript.
- Set up FastAPI and validated schemas.
- Set up PostgreSQL and PostGIS.
- Implement initial migrations.
- Implement the source registry.
- Create deterministic simulated fixtures for every requested category.
- Implement the common signal schema.
- Build the map and layer controls.
- Implement viewport-bounded signal queries.
- Add clustering and basic filtering.
- Add signal detail panels.
- Implement health and source-status endpoints.
- Add automated normalization tests.

**Gate:** The complete map interface works with labeled simulated data, without pretending to have live provider connectivity.

### Phase 2 — First real-data integrations

- Select at least two providers with verified usage permissions.
- Implement their provider adapters.
- Validate actual responses.
- Normalize geometries, timestamps, and identifiers.
- Implement deduplication and updated-record handling.
- Add data-source attribution.
- Add provider timeout and rate-limit handling.
- Track ingestion runs and source health.
- Test missing and malformed fields.
- Compare normalized output with the original source record.

**Gate:** At least two real integrations work end-to-end, with source provenance and error states visible in the UI.

### Phase 3 — Multi-layer experience

- Add source-specific layer renderers.
- Implement timeline filters.
- Add category and source filters.
- Add time-range selection.
- Improve marker clustering.
- Add layer-specific freshness states.
- Implement partial-data behavior.
- Add saved filters or views if needed.
- Test map performance under realistic record counts.

**Gate:** A provider failure does not hide unrelated layers, and users can filter the map without receiving unbounded data payloads.

### Phase 4 — Remaining signal categories

- Add aircraft integration once the provider and intended use are approved.
- Add vessel integration once data access and licensing are verified.
- Add satellite or Earth-observation metadata.
- Add earthquake catalog integration.
- Add authorized weather data.
- Add public-camera metadata or explicitly permitted feeds.
- Add open geographic infrastructure data.
- Verify each category's schema and display semantics.
- Document each provider's coverage and limitations.
- Test independent layer failures and stale data.

**Gate:** Each category has an independently tested adapter, an explicit provider status, and visible provenance.

### Phase 5 — Temporal analysis and event context

- Implement historical queries where permitted.
- Add event detail views.
- Add nearby-signal searches.
- Implement deterministic spatial-temporal correlation rules.
- Preserve source records behind each association.
- Add explanation of matching criteria.
- Add time and distance boundaries.
- Test false associations and time-zone edge cases.
- Add export of selected normalized records when permitted.

**Gate:** Cross-layer associations are explainable and are not presented as proven causal relationships without supporting evidence.

### Phase 6 — Optional AI-assisted explanation

- Define supported assistant tasks.
- Implement approved-source retrieval.
- Pass only the evidence needed for the current request.
- Require structured output.
- Associate factual claims with source references.
- Add unsupported-claim and prompt-injection tests.
- Prevent the assistant from generating private-person dossiers or sensitive operational targeting.
- Make evidence and uncertainty visible.
- Evaluate the assistant against a versioned test dataset.

**Gate:** Every significant factual summary can be checked against underlying source records, and the system acknowledges missing evidence.

