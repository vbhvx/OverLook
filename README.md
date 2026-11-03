# OverLook — Public Signal Intelligence & Situational Awareness Platform

> One map for aircraft, ships, satellites, earthquakes, weather, public cameras and infrastructure. Every signal carries its source, freshness and limitations, and nothing is shown as fact unless the evidence supports it.

**Status: specification stage.** This repository currently holds the technical specification ([`Overlook.md`](./Overlook.md)). No application code has been written yet. Everything below describes the planned system.

---

## Overview

Investigating what is happening in an area usually means switching between separate aircraft trackers, ship trackers, satellite dashboards, earthquake feeds, weather services and camera directories. OverLook consolidates public, authorized and appropriately licensed signals into one interactive workspace.

It is more than datasets stacked on a map. OverLook normalizes space and time across sources, shows where each record came from and how fresh it is, keeps different data types distinct, and helps users explore possibly related events without presenting speculation as established fact.

**Priority order:** source verification → data correctness → spatial and temporal normalization → trustworthy multi-layer visualization → cross-source exploration → event correlation → performance → testing → deployment.

## Signal categories

| Category | Candidate source | Key caveat |
|---|---|---|
| Aircraft | [OpenSky Network](https://openskynetwork.github.io/opensky-api/rest.html) | Rate limits; commercial use needs consent |
| Ships | Provider to be selected (authorized AIS) | No scraping; public visibility is not API access |
| Satellites | Public orbital data + [Copernicus Data Space](https://documentation.dataspace.copernicus.eu/APIs.html) | Orbit position is not an image acquisition |
| Earthquakes | [USGS Earthquake Catalog](https://earthquake.usgs.gov/fdsnws/event/1/) | Events are revised; keep history |
| Weather | [Open-Meteo](https://open-meteo.com/) (subject to terms) | Forecasts are never observations |
| Public cameras | Explicitly public, authorized feeds only | Metadata and links; no private CCTV |
| Infrastructure | [OpenStreetMap](https://www.openstreetmap.org/) / open datasets | Hosted tile and geocoder policies apply |

The first release does not need a live integration for every category. It does need a source registry, a reusable adapter architecture, clearly labeled simulated fixtures, and an honest status for each integration. At least two real-data integrations are required, chosen after inspecting the sources.

## Planned features

- Interactive global map (MapLibre GL JS) with toggleable, independently filterable layers
- Search and filter by area, time range, category and entity or event
- Timeline for navigating signals by observation time
- Source-aware detail panel: original record link, attribution, timestamps, freshness, data status
- Source registry with health, capability and disabled states
- Event investigation workspace with deterministic, explainable correlations
- Optional AI-assisted explanation, grounded in stored evidence

## Data correctness principles

- Coordinates are validated and normalized; timestamps are stored in UTC with source time and timezone preserved.
- Observation, publication, ingestion and valid times are kept separate.
- Source identifiers and original links are preserved; re-ingestion never creates duplicate signals.
- Missing data stays missing and is never turned into zero.
- Stale, delayed, unavailable and simulated data are clearly labeled.
- Records are never joined just because they are geographically close. Cross-source correlations are shown as hypotheses unless the evidence supports more.
- Real-time updates, locations, source records and incident explanations are never fabricated.

## Architecture

```text
Public / Authorized Data Sources
    (aircraft · vessels · satellites · earthquakes · weather · cameras · infrastructure)
               │
               ▼
        Provider Adapters
               │
               ▼
   Validation + Normalization
               │
               ▼
     PostgreSQL + PostGIS
               │
               ▼
   Query / Correlation API (FastAPI)
               │
       ┌───────┴────────┐
       ▼                ▼
   Map layers      Timeline /
   and filters     Event detail
       └───────┬────────┘
               ▼
        React dashboard
```

**Core rule:** the map is a presentation layer, not the source of truth. Provider access is centralized in the backend, never called from the browser, so rate limits, credentials and licensing are enforced in one place.

### Tech stack

| Layer | Choice |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Map | MapLibre GL JS |
| Backend | Python, FastAPI, `httpx`, Pydantic |
| Geospatial | PostgreSQL + PostGIS, Shapely/GeoPandas where justified |
| Cache / jobs | Redis or TTL cache; worker + queue only if needed |
| Charts | Recharts or similar |
| Testing | pytest, Vitest, Playwright |
| Tooling | Docker Compose |

## API (planned)

Versioned under `/api/v1`, with typed schemas, request IDs, bounded queries and explicit freshness, partial-data and provider-error states.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Service health and readiness |
| `GET /sources` | Registered sources and status |
| `GET /layers` | Map layers and metadata |
| `GET /signals` | Query by bounds, time, category and source |
| `GET /signals/{signalId}` | Signal with provenance |
| `GET /timeline` | Aggregated signals over time |
| `GET /events`, `GET /events/{eventId}` | Events and deterministic correlations |
| `GET /regions` | Supported regions and saved public areas |
| `GET /map/summary` | Viewport-level counts and layer summaries |

Example:

```
GET /api/v1/signals?category=earthquake&start=2026-10-01T00:00:00Z&end=2026-10-02T00:00:00Z&bbox=-10,35,5,45&limit=500
```

## Planned repository layout

```text
frontend/     React + TypeScript app (map, layers, timeline, events, api)
backend/      FastAPI app (api, providers, ingestion, geospatial, correlation, tests)
database/     migrations and seeds
tests/e2e/    Playwright tests
docs/         architecture, sources, data-model, api, data-policy, deployment
docker-compose.yml
.env.example
```

## Roadmap

| Phase | Goal |
|---|---|
| 0 | Verify source contracts, licensing and rate limits before building on them |
| 1 | Core map and normalized data model |
| 2 | First real-data integrations (at least two) |
| 3 | Multi-layer experience |
| 4 | Remaining signal categories |
| 5 | Temporal analysis and event context |
| 6 | Optional AI-assisted explanation |
| 7 | Hardening and deployment |

**Phase 0 stop condition:** do not build the full real-data visualization around an assumed API contract. First confirm the source supplies the fields the UI needs, under terms that permit the intended use.

## Responsible use

OverLook is an analytical information system. It must communicate the uncertainty and limits of public data and must not claim comprehensive real-world visibility.

Out of scope, by design:

- Accessing private cameras or bypassing authentication
- Face recognition or identifying people in footage
- Profiling, tracking or inferring routines of private individuals
- Tactical targeting or operational tracking for violent purposes
- Exposing weaknesses or non-public details of sensitive infrastructure
- Redistributing commercial datasets without permission
- Linking an aircraft, vessel or satellite to an incident without supporting evidence

Security rules include no endpoint that fetches arbitrary client-supplied URLs (SSRF), no provider secrets or stack traces in responses, and validation of any webhook sender and signature.

## Documentation

The full specification, covering data-source contracts, normalization and correlation logic, database schema, UI requirements, test plan and risks, is in [`Overlook.md`](./Overlook.md).

## License

Not yet chosen.
