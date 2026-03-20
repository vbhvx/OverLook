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

