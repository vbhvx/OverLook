# backend/app/providers/opensky_aircraft.py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.config import settings
from backend.app.geospatial.validation import validate_coordinates
from backend.app.providers.base import BaseProviderAdapter, compute_record_hash, logger
from backend.app.schemas.signals import (
    DataStatus,
    GeoJSONGeometry,
    GeometryType,
    SignalCategory,
    SignalEnvelope,
    SourceAttributionRef,
)


class OpenSkyAircraftAdapter(BaseProviderAdapter):
    source_id = "opensky-network"
    category = "aircraft"
    name = "The OpenSky Network"
    API_URL = "https://opensky-network.org/api/states/all"

    def __init__(self):
        super().__init__()
        self._cached_signals: List[SignalEnvelope] = []

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        params: Dict[str, Any] = {}
        # If no bbox provided, default to a high-traffic bounding box (e.g., SF Bay corridor)
        # to respect OpenSky rate limits and avoid requesting the entire global vector table
        if bbox and len(bbox) >= 4:
            params["lomin"] = max(-180.0, bbox[0])
            params["lamin"] = max(-90.0, bbox[1])
            params["lomax"] = min(180.0, bbox[2])
            params["lamax"] = min(90.0, bbox[3])
        else:
            # Default to SF Bay / Northern California
            params["lomin"] = -123.5
            params["lamin"] = 36.8
            params["lomax"] = -121.2
            params["lamax"] = 38.8

        signals: List[SignalEnvelope] = []
        now_utc = datetime.now(timezone.utc)
        auth = None
        if settings.OPENSKY_USERNAME and settings.OPENSKY_PASSWORD:
            auth = (settings.OPENSKY_USERNAME, settings.OPENSKY_PASSWORD)

        try:
            async with self.get_http_client() as client:
                resp = await client.get(self.API_URL, params=params, auth=auth)

                if resp.status_code == 200:
                    data = resp.json()
                    states = data.get("states") or []
                    time_epoch = data.get("time")
                    obs_time = (
                        datetime.fromtimestamp(time_epoch, tz=timezone.utc)
                        if time_epoch else now_utc
                    )

                    for s in states[:100]: # Bound to 100 flights per region
                        try:
                            # OpenSky state vector format:
                            # 0: icao24, 1: callsign, 2: origin_country, 3: time_position, 4: last_contact,
                            # 5: longitude, 6: latitude, 7: baro_altitude, 8: on_ground, 9: velocity,
                            # 10: true_track, 11: vertical_rate, 12: sensors, 13: geo_altitude, 14: squawk, 15: spi, 16: position_source
                            icao24 = s[0]
                            callsign = (s[1] or "").strip()
                            origin_country = s[2]
                            lon_val = s[5]
                            lat_val = s[6]
                            baro_alt = s[7]
                            on_ground = bool(s[8])
                            velocity_ms = s[9]
                            heading_deg = s[10]
                            vertical_rate = s[11]
                            squawk = s[14]

                            if lon_val is None or lat_val is None:
                                continue

                            lon, lat = validate_coordinates(float(lon_val), float(lat_val))

                            pos_time_epoch = s[3]
                            pos_observed_at = (
                                datetime.fromtimestamp(pos_time_epoch, tz=timezone.utc)
                                if pos_time_epoch else obs_time
                            )

                            signal = SignalEnvelope(
                                id=f"ac-{icao24}",
                                sourceId=self.source_id,
                                sourceRecordId=icao24,
                                category=SignalCategory.AIRCRAFT,
                                signalType="state-vector",
                                geometry=GeoJSONGeometry(
                                    type=GeometryType.POINT,
                                    coordinates=[lon, lat, baro_alt] if baro_alt is not None else [lon, lat]
                                ),
                                latitude=lat,
                                longitude=lon,
                                altitudeM=baro_alt,
                                observedAt=pos_observed_at,
                                publishedAt=obs_time,
                                ingestedAt=now_utc,
                                dataStatus=DataStatus.ACTUAL,
                                isSimulated=False,
                                sourceUrl="https://opensky-network.org/",
                                source=SourceAttributionRef(
                                    id=self.source_id,
                                    name=self.name,
                                    recordUrl="https://opensky-network.org/",
                                    attribution="Data courtesy of The OpenSky Network (https://opensky-network.org)"
                                ),
                                metadata={
                                    "icao24": icao24,
                                    "callsign": callsign if callsign else None,
                                    "originCountry": origin_country,
                                    "velocityMs": velocity_ms,
                                    "velocityKnots": round(velocity_ms * 1.94384, 1) if velocity_ms is not None else None,
                                    "headingDeg": heading_deg,
                                    "verticalRateMs": vertical_rate,
                                    "onGround": on_ground,
                                    "squawk": squawk
                                },
                                rawRecordHash=compute_record_hash(s),
                                lastSeenAt=now_utc
                            )
                            signals.append(signal)
                        except Exception:
                            logger.debug("skipping malformed record", extra={"source": self.source_id}, exc_info=True)
                            continue

                    self.last_sync_at = now_utc
                    self.last_status = "active"
                    self.last_error = None
                    self._cached_signals = signals
                elif resp.status_code == 429:
                    self.last_status = "rate_limited"
                    self.last_error = "OpenSky API rate limit exceeded (HTTP 429). Utilizing cached or simulated signals."
                    return self._cached_signals
                else:
                    self.last_status = "degraded"
                    self.last_error = f"OpenSky responded with HTTP {resp.status_code}"
                    return self._cached_signals
        except Exception as e:
            self.last_status = "degraded"
            self.last_error = str(e)
            return self._cached_signals

        return signals

    async def check_health(self) -> Dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "status": self.last_status,
            "cachedCount": len(self._cached_signals),
            "lastSyncAt": self.last_sync_at,
            "lastError": self.last_error,
            "isLive": True
        }

