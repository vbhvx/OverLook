# Source Registry & Data Provider Specifications

Every intelligence feed ingested into OverLook is treated as an isolated provider integration with explicit licensing, rate limiting, and attribution boundaries.

| Source ID | Category | Provider Organization | Protocol | Status | License / Redistribution Terms | Attribution Requirements |
|---|---|---|---|---|---|---|
| `usgs-earthquakes` | Earthquake | U.S. Geological Survey (USGS) | GeoJSON REST API | **Live Active** | Public Domain / Unrestricted | "Data courtesy of the U.S. Geological Survey (USGS)" |
| `open-meteo` | Weather | Open-Meteo.com | JSON REST API | **Live Active** | Open-Meteo Terms / CC BY 4.0 | "Weather data by Open-Meteo.com under CC BY 4.0" |
| `opensky-network` | Aircraft | The OpenSky Network | JSON REST API | **Live Active** | Academic Open / Non-Commercial | "The OpenSky Network, https://opensky-network.org" |
| `global-ais-maritime` | Vessel | Maritime Safety Info / Authorized AIS | AIS Stream / GeoJSON | **Sample / Live** | Authorized Public Sample | "Public Maritime Safety Information & Demonstrator AIS" |
| `copernicus-dataspace` | Satellite | Copernicus Data Space Ecosystem | STAC / OData Catalog | **Catalog Sample** | Copernicus Open Access | "Contains modified Copernicus Sentinel data [2026]" |
| `public-dot-cameras` | Camera | State & Municipal DOT (Caltrans / WSDOT) | Public Web Snapshot | **Live Active** | Public viewing only | "State & Regional Department of Transportation feeds" |
| `osm-critical-infra` | Infrastructure | OpenStreetMap Contributors | OSM Overpass Extract | **Live Active** | Open Database License (ODbL) | "© OpenStreetMap contributors under ODbL" |

## Provider Details

### 1. USGS Earthquake Hazards Program
- **Endpoint**: `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson`
- **Fields Extracted**: `id`, `mag`, `magType`, `time` (epoch ms), `updated`, `place`, `coordinates` `[lon, lat, depth_km]`, `tsunami`, `alert`, `status` (`automatic` vs `reviewed`).
- **Update Handling**: USGS updates existing events as seismic analysts review waveforms. OverLook updates matching signal IDs without duplicating hypocenters.

### 2. Open-Meteo Weather API
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Fields Extracted**: `temperature_2m`, `relative_humidity_2m`, `precipitation`, `weather_code`, `wind_speed_10m`, `wind_direction_10m`, `surface_pressure`.
- **Forecast vs Observation Principle**: Real-time readings are tagged `dataStatus: "actual"`. Model forecasts are tagged `dataStatus: "forecast"` with explicit `validFrom` and `validUntil` intervals.

### 3. OpenSky Network
- **Endpoint**: `https://opensky-network.org/api/states/all`
- **Fields Extracted**: `icao24`, `callsign`, `origin_country`, `time_position`, `longitude`, `latitude`, `baro_altitude`, `velocity`, `true_track`, `vertical_rate`, `squawk`.
- **Rate Limit Policy**: Anonymous access is rate-limited. On HTTP 429, OverLook transitions provider health to `rate_limited` and falls back to cached vectors and simulated demonstrators.

### 4. DOT Public Cameras
- **Authorized Public Scope**: Only explicitly public, non-authenticated DOT cameras are registered (e.g. SF Bay Bridge anchorage, Golden Gate plaza).
- **Privacy Restrictions**: Video frame retention is disabled by default. Facial recognition, biometric analysis, and private CCTV surveillance are strictly out of scope.

