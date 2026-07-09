# OverLook

OverLook is a situational-awareness workspace that brings public geospatial signals into one map and timeline interface. The backend models sources, layers, events, regions, and signals, and includes provider adapters for earthquakes, weather, aircraft, vessels, satellite catalog data, public cameras, and infrastructure. Provider availability varies; the application also includes fixtures for development.

## Architecture

- `backend/app/providers` — isolated upstream-provider adapters.
- `backend/app/ingestion` and `correlation` — synchronization, fixture data, and spatial-temporal correlation.
- `backend/app/api/v1` — FastAPI endpoints for map data, signals, events, layers, sources, regions, timeline, and health.
- `frontend/src` — Vite/React map interface built with MapLibre GL.
- `database/migrations` and `database/seeds` — PostGIS schema and seed records.

The production-style stack uses FastAPI, async PostgreSQL/PostGIS, and React 18/TypeScript. Correlation indicates proximity based on the application rules; it is not evidence of causation.

## Start locally

Docker is the supported integrated setup:

```bash
cd 28_OverLook
cp .env.example .env
docker compose up --build
```

This starts PostGIS, the API on port 8000, and the UI on port 3000 (also mapped to port 80). The migration and seed SQL files are mounted into the database container on first initialization.

For UI-only development:

```bash
cd frontend
npm install
npm run dev
```

Use `npm run build` to type-check and build the frontend. Backend dependencies are listed in `backend/requirements.txt`; tests are under `backend/tests` and `tests/e2e`.

## Configuration

`.env.example` is authoritative. Common settings are:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/overlook
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
OPENSKY_USERNAME=
OPENSKY_PASSWORD=
ENABLE_BACKGROUND_SYNC=true
```

Credentials for live providers are optional. Keep them out of source control and use the defaults/fixtures when provider access is unavailable.
