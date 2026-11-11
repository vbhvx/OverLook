# backend/app/providers/usgs_earthquake.py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


class USGSEarthquakeAdapter(BaseProviderAdapter):
    source_id = "usgs-earthquakes"
    category = "earthquake"
    name = "USGS Earthquake Hazards Program"
    API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        params = {
            "format": "geojson",
            "limit": 150,
            "minmagnitude": 2.0
        }
        if bbox and len(bbox) >= 4:
            params["minlongitude"] = bbox[0]
            params["minlatitude"] = bbox[1]
            params["maxlongitude"] = bbox[2]
            params["maxlatitude"] = bbox[3]

        signals: List[SignalEnvelope] = []
        try:
            async with self.get_http_client() as client:
                resp = await client.get(self.API_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    features = data.get("features", [])
                    now_utc = datetime.now(timezone.utc)

                    for feat in features:
                        try:
                            f_id = feat.get("id")
                            props = feat.get("properties", {})
                            geom = feat.get("geometry", {})
                            coords = geom.get("coordinates", [])

                            if len(coords) < 2:
                                continue

                            lon, lat = validate_coordinates(coords[0], coords[1])
                            depth_km = float(coords[2]) if len(coords) > 2 else None

                            time_ms = props.get("time")
                            if time_ms is None:
                                continue
                            observed_at = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)

                            updated_ms = props.get("updated")
                            published_at = (
                                datetime.fromtimestamp(updated_ms / 1000.0, tz=timezone.utc)
                                if updated_ms else None
                            )

                            mag = props.get("mag")
                            mag_type = props.get("magType")
                            place = props.get("place", "Unknown Location")
                            status = props.get("status", "automatic")
                            url = props.get("url")
                            tsunami = bool(props.get("tsunami", 0))
                            alert = props.get("alert") # green, yellow, orange, red

                            raw_hash = compute_record_hash(feat)

                            signal = SignalEnvelope(
                                id=f"eq-{f_id}",
                                sourceId=self.source_id,
                                sourceRecordId=str(f_id),
                                category=SignalCategory.EARTHQUAKE,
                                signalType="seismic-event",
                                geometry=GeoJSONGeometry(
                                    type=GeometryType.POINT,
                                    coordinates=[lon, lat, depth_km] if depth_km is not None else [lon, lat]
                                ),
                                latitude=lat,
                                longitude=lon,
                                altitudeM=-(depth_km * 1000.0) if depth_km is not None else None,
                                observedAt=observed_at,
                                publishedAt=published_at,
                                ingestedAt=now_utc,
                                dataStatus=DataStatus.ACTUAL,
                                isSimulated=False,
                                sourceUrl=url,
                                source=SourceAttributionRef(
                                    id=self.source_id,
                                    name=self.name,
                                    recordUrl=url,
                                    attribution="Data courtesy of the U.S. Geological Survey (USGS)"
                                ),
                                metadata={
                                    "magnitude": mag,
                                    "magnitudeType": mag_type,
                                    "depthKm": depth_km,
                                    "place": place,
                                    "reviewStatus": status,
                                    "tsunamiWarning": tsunami,
                                    "usgsAlert": alert,
                                    "feltReports": props.get("felt"),
                                    "cdi": props.get("cdi"),
                                    "mmi": props.get("mmi")
                                },
                                rawRecordHash=raw_hash,
                                lastSeenAt=now_utc
                            )
                            signals.append(signal)
                        except Exception:
                            logger.debug("skipping malformed record", extra={"source": self.source_id}, exc_info=True)
                            continue

                    self.last_sync_at = now_utc
                    self.last_status = "active"
                    self.last_error = None
                else:
                    self.last_status = "degraded"
                    self.last_error = f"USGS API responded with HTTP {resp.status_code}"
        except Exception as e:
            self.last_status = "degraded"
            self.last_error = str(e)

        return signals

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with self.get_http_client() as client:
                resp = await client.get(self.API_URL, params={"format": "geojson", "limit": 1})
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

