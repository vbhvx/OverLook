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

