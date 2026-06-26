# backend/app/providers/open_meteo.py
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import httpx
from backend.app.providers.base import BaseProviderAdapter, compute_record_hash
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry,
    GeometryType, SourceAttributionRef
)
from backend.app.geospatial.validation import validate_coordinates

WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

# Monitoring Stations across key strategic corridors
WEATHER_STATIONS = [
    {"name": "San Francisco Bay Station", "lat": 37.7749, "lon": -122.4194},
    {"name": "Oakland Maritime Hub", "lat": 37.8044, "lon": -122.2712},
    {"name": "San Jose Met Observation", "lat": 37.3382, "lon": -121.8863},
    {"name": "Hawaii Mauna Loa Obs", "lat": 19.4795, "lon": -155.6028},
    {"name": "Honolulu Coastal Station", "lat": 21.3069, "lon": -157.8583},
    {"name": "Dover Strait Maritime Met", "lat": 51.1279, "lon": 1.3134},
    {"name": "English Channel Offshore", "lat": 50.1500, "lon": -0.5000},
    {"name": "Mediterranean Strait Station", "lat": 36.1408, "lon": -5.3536},
    {"name": "Rome Tyrrhenian Met", "lat": 41.9028, "lon": 12.4964},
    {"name": "Tokyo Bay Marine Observatory", "lat": 35.6190, "lon": 139.7514},
    {"name": "Yokohama Port Met", "lat": 35.4437, "lon": 139.6380},
    {"name": "Singapore Malacca Coastal", "lat": 1.3521, "lon": 103.8198}
]

class OpenMeteoAdapter(BaseProviderAdapter):
    source_id = "open-meteo"
    category = "weather"
    name = "Open-Meteo Weather Forecast API"
    API_URL = "https://api.open-meteo.com/v1/forecast"

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        signals: List[SignalEnvelope] = []
        now_utc = datetime.now(timezone.utc)
        
        # Filter stations if bbox provided
        target_stations = WEATHER_STATIONS
        if bbox and len(bbox) >= 4:
            w, s, e, n = bbox[0], bbox[1], bbox[2], bbox[3]
            filtered = [
                st for st in WEATHER_STATIONS
                if s <= st["lat"] <= n and (
                    w <= st["lon"] <= e if w <= e else (st["lon"] >= w or st["lon"] <= e)
                )
            ]
            if filtered:
                target_stations = filtered

        # Query batch of stations
        async with self.get_http_client() as client:
            for station in target_stations[:8]: # Bounded concurrent requests
                try:
                    params = {
                        "latitude": station["lat"],
                        "longitude": station["lon"],
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure",
                        "hourly": "temperature_2m,precipitation_probability,weather_code",
                        "forecast_days": 1,
                        "timezone": "UTC"
                    }
                    resp = await client.get(self.API_URL, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        current = data.get("current", {})
                        
                        lon, lat = validate_coordinates(station["lon"], station["lat"])
                        code = current.get("weather_code", 0)
                        desc = WEATHER_CODE_MAP.get(code, f"Code {code}")
                        
                        # 1. Observed Real-time Signal
                        obs_signal = SignalEnvelope(
                            id=f"wx-obs-{station['name'].lower().replace(' ', '-')}",
                            sourceId=self.source_id,
                            sourceRecordId=f"{lat}_{lon}_{current.get('time')}",
                            category=SignalCategory.WEATHER,
                            signalType="weather-observation",
                            geometry=GeoJSONGeometry(
                                type=GeometryType.POINT,
                                coordinates=[lon, lat]
                            ),
                            latitude=lat,
                            longitude=lon,
                            observedAt=now_utc,
                            publishedAt=now_utc,
                            ingestedAt=now_utc,
                            validFrom=now_utc - timedelta(minutes=15),
                            validUntil=now_utc + timedelta(minutes=45),
                            dataStatus=DataStatus.ACTUAL,
                            isSimulated=False,
                            sourceUrl="https://open-meteo.com/en/docs",
                            source=SourceAttributionRef(
                                id=self.source_id,
                                name=self.name,
                                recordUrl="https://open-meteo.com/",
                                attribution="Weather data by Open-Meteo.com under CC BY 4.0"
                            ),
                            metadata={
                                "stationName": station["name"],
                                "isForecast": False,
                                "weatherCondition": desc,
                                "weatherCode": code,
                                "temperatureC": current.get("temperature_2m"),
                                "feelsLikeC": current.get("apparent_temperature"),
                                "humidityPercent": current.get("relative_humidity_2m"),
                                "precipitationMm": current.get("precipitation"),
                                "windSpeedKmh": current.get("wind_speed_10m"),
                                "windDirectionDeg": current.get("wind_direction_10m"),
                                "surfacePressureHpa": current.get("surface_pressure"),
                                "observationInterval": current.get("interval", 900)
                            },
                            rawRecordHash=compute_record_hash(current),
                            lastSeenAt=now_utc
                        )
                        signals.append(obs_signal)
                        
                        # 2. Hourly Forecast Signal (Explicitly labeled as forecast, valid 3 hours ahead)
                        hourly = data.get("hourly", {})
                        h_times = hourly.get("time", [])
                        h_temps = hourly.get("temperature_2m", [])
                        h_codes = hourly.get("weather_code", [])
                        h_precip = hourly.get("precipitation_probability", [])
                        
                        if len(h_times) > 3:
                            f_idx = 3 # 3 hours ahead
                            f_valid_from = now_utc + timedelta(hours=3)
                            f_valid_until = now_utc + timedelta(hours=4)
                            f_code = h_codes[f_idx] if len(h_codes) > f_idx else 0
                            
                            fcst_signal = SignalEnvelope(
                                id=f"wx-fcst-{station['name'].lower().replace(' ', '-')}",
                                sourceId=self.source_id,
                                sourceRecordId=f"fcst_{lat}_{lon}_{h_times[f_idx]}",
                                category=SignalCategory.WEATHER,
                                signalType="weather-forecast",
                                geometry=GeoJSONGeometry(
                                    type=GeometryType.POINT,
                                    coordinates=[lon, lat]
                                ),
                                latitude=lat,
                                longitude=lon,
                                observedAt=now_utc, # Model run/issue time
                                publishedAt=now_utc,
                                ingestedAt=now_utc,
                                validFrom=f_valid_from,
                                validUntil=f_valid_until,
                                dataStatus=DataStatus.FORECAST, # Clearly distinguished from observation!
                                isSimulated=False,
                                sourceUrl="https://open-meteo.com/en/docs",
                                source=SourceAttributionRef(
                                    id=self.source_id,
                                    name=self.name,
                                    recordUrl="https://open-meteo.com/",
                                    attribution="Weather data by Open-Meteo.com under CC BY 4.0"
                                ),
                                metadata={
                                    "stationName": station["name"],
                                    "isForecast": True,
                                    "forecastHorizonHours": 3,
                                    "weatherCondition": WEATHER_CODE_MAP.get(f_code, f"Code {f_code}"),
                                    "weatherCode": f_code,
                                    "predictedTemperatureC": h_temps[f_idx] if len(h_temps) > f_idx else None,
                                    "precipitationProbability": h_precip[f_idx] if len(h_precip) > f_idx else None,
                                    "forecastModel": "ECMWF / GFS seamless ensemble"
                                },
                                rawRecordHash=compute_record_hash(f"{station['name']}_{h_times[f_idx]}"),
                                lastSeenAt=now_utc
                            )
                            signals.append(fcst_signal)

                except Exception as ex:
                    continue

        self.last_sync_at = now_utc
        self.last_status = "active" if signals else "degraded"
        return signals

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with self.get_http_client() as client:
                resp = await client.get(
                    self.API_URL,
                    params={"latitude": 37.77, "longitude": -122.42, "current": "temperature_2m"}
                )
                return {
                    "sourceId": self.source_id,
                    "status": "healthy" if resp.status_code == 200 else "degraded",
                    "statusCode": resp.status_code,
                    "lastSyncAt": self.last_sync_at,
                    "isLive": True
                }
        except Exception as e:
            return {
                "sourceId": self.source_id,
                "status": "offline",
                "error": str(e),
                "isLive": True
            }

