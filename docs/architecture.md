# System Architecture — OverLook Platform

## Overview

OverLook is a full-stack public signal intelligence and geospatial situational awareness platform designed to consolidate heterogeneous public data feeds into a unified analytical map workspace.

```text
Public / Authorized Data Sources
    ├── Aircraft (OpenSky Network)
    ├── Vessels (AIS Maritime Transponders)
    ├── Satellite / Earth Observation (Copernicus Data Space)
    ├── Earthquakes (USGS Earthquake Hazards Program)
    ├── Weather (Open-Meteo API)
    ├── Public Cameras (State / Municipal DOT)
    └── Infrastructure (OpenStreetMap Public Extract)
               |
               v
      Provider Adapters (Isolated contracts & rate-limit handling)
               |
               v
   Validation + Normalization (WGS84, UTC timestamps, schema envelope)
               |
               v
   PostgreSQL + PostGIS / SQLite Spatial Repository
               |
               v
   Correlation Engine (Deterministic spatial-temporal hypotheses)
               |
       ┌───────┴────────┐
       v                v
   Map Layers        Timeline /
   and Filters       Event Detail
       └───────┬────────┘
               v
     React + MapLibre GL JS Dashboard
```

## Core Architectural Invariants

1. **The Map is a Presentation Layer, Not the Truth**:
   - The map visualizes validated, normalized records without inventing positions or interpolating synthetic paths.
2. **Provider Isolation**:
   - Every provider adapter executes independently. If OpenSky rate limits or Open-Meteo is temporarily unreachable, earthquake and infrastructure layers remain functional.
3. **Temporal Normalization**:
   - Every signal maintains distinct timestamps for physical observation, source publication, system ingestion, and validity interval (`valid_from` to `valid_until`). Ingestion time never overwrites observation time.
4. **Spatial Correctness**:
   - Coordinates are strictly WGS84 `[longitude, latitude]`. Automatic sanity checks catch inverted latitude/longitude orders, non-finite values, and antimeridian crossing bounds (`west > east`).
5. **Deterministic Cross-Source Correlation**:
   - Proximity does not imply causation. Associations between seismic events, weather observations, and civil infrastructure are transparently calculated via great-circle distance and temporal delta thresholds, accompanied by explicit analytical disclaimers.

