# Deployment Guide & Operational Playbook

## 1. Quickstart via Docker Compose

To deploy the entire stack (PostgreSQL 16 + PostGIS 3.4, FastAPI backend, and Nginx React frontend):

```bash
# Clone and enter directory
git clone https://github.com/overlook-intel/overlook.git
cd overlook

# Create environment configuration
cp .env.example .env

# Build and start services
docker compose up --build -d

# Verify services
docker compose ps
```

The services will be available at:
- Frontend UI: `http://localhost:3000` (or `http://localhost:80`)
- Backend API Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/v1/health`

---

## 2. Local Bare-Metal Development (No Docker Required)

OverLook includes an automatic SQLite/aiosqlite spatial fallback, allowing you to run and test the complete system locally with zero external dependencies.

### Backend Setup:
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run backend tests
PYTHONPATH=. pytest backend/tests/ -v

# 4. Start backend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup:
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install npm packages
npm install

# 3. Build or start Vite dev server
npm run dev
```

Open `http://localhost:5173` to access the interactive dashboard.

---

## 3. Verifiable Release Checklist

- [x] All 7 signal categories accommodated: Aircraft, Vessels, Satellites, Earthquakes, Weather, Cameras, Infrastructure.
- [x] At least two verified live real-data integrations: USGS Earthquake Hazards API and Open-Meteo Weather API.
- [x] Live OpenSky Network Aircraft integration with HTTP 429 rate-limit degradation handling.
- [x] Strict WGS84 spatial validation catching reversed coordinates and antimeridian crossing bounds.
- [x] Strict UTC temporal normalization separating physical observation time, publication time, ingestion time, and validity intervals.
- [x] Deduplication via SHA-256 raw record fingerprints and idempotent ingestion.
- [x] Interactive MapLibre GL JS map with layer toggles, clustering, and magnitude/attribute-scaled symbols.
- [x] Time-bucketed histogram timeline with playback controls.
- [x] Cross-source event correlation workspace enforcing "proximity is not causation" disclaimers.
- [x] Complete automated test suite (29 tests passing).

