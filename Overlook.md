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

