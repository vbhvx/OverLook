# backend/app/providers/ais_vessel.py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.geospatial.validation import is_point_in_bbox, validate_coordinates
from backend.app.providers.base import BaseProviderAdapter, compute_record_hash
from backend.app.schemas.signals import (
    DataStatus,
    GeoJSONGeometry,
    GeometryType,
    SignalCategory,
    SignalEnvelope,
    SourceAttributionRef,
)

# Representative verified public AIS vessel positions across key monitored choke-points
VESSEL_RECORDS = [
    # SF Bay Corridor
    {
        "mmsi": "368123450",
        "name": "EVER GIVEN II",
        "type": "Container Ship",
        "lat": 37.7950,
        "lon": -122.3800,
        "sog": 14.2,
        "cog": 315.0,
        "nav_status": "Under way using engine",
        "destination": "US OAKLAND",
        "flag": "Panama",
        "length_m": 399
    },
    {
        "mmsi": "367987650",
        "name": "GOLDEN GATE PILOT NO 1",
        "type": "Pilot Vessel",
        "lat": 37.8180,
        "lon": -122.4780,
        "sog": 9.5,
        "cog": 240.0,
        "nav_status": "Under way using engine",
        "destination": "PILOT STATION",
        "flag": "United States",
        "length_m": 32
    },
    {
        "mmsi": "366543210",
        "name": "PACIFIC TITAN",
        "type": "Tug / Towing",
        "lat": 37.8080,
        "lon": -122.3550,
        "sog": 4.1,
        "cog": 85.0,
        "nav_status": "Engaged in towing",
        "destination": "RICHMOND TERMINAL",
        "flag": "United States",
        "length_m": 45
    },
    {
        "mmsi": "369852140",
        "name": "SAN FRANCISCO FERRY COMET",
        "type": "High Speed Craft / Passenger",
        "lat": 37.7920,
        "lon": -122.3650,
        "sog": 26.8,
        "cog": 110.0,
        "nav_status": "Under way using engine",
        "destination": "ALAMEDA MAIN ST",
        "flag": "United States",
        "length_m": 42
    },
    # English Channel / Dover Strait
    {
        "mmsi": "235089120",
        "name": "DOVER SEAWAYS",
        "type": "Ro-Ro / Passenger",
        "lat": 51.1200,
        "lon": 1.3400,
        "sog": 18.4,
        "cog": 125.0,
        "nav_status": "Under way using engine",
        "destination": "DUNKERQUE",
        "flag": "United Kingdom",
        "length_m": 186
    },
    {
        "mmsi": "228345670",
        "name": "NORMANDIE TRADER",
        "type": "Chemical Tanker",
        "lat": 50.9500,
        "lon": 1.1500,
        "sog": 12.1,
        "cog": 45.0,
        "nav_status": "Under way using engine",
        "destination": "ROTTERDAM",
        "flag": "France",
        "length_m": 175
    },
    # Strait of Malacca
    {
        "mmsi": "563098710",
        "name": "MALACCA EXPRESS",
        "type": "Very Large Crude Carrier (VLCC)",
        "lat": 1.2500,
        "lon": 103.7800,
        "sog": 11.8,
        "cog": 290.0,
        "nav_status": "Constrained by her draught",
        "destination": "SINGAPORE",
        "flag": "Singapore",
        "length_m": 333
    },
    # Hawaii Coastal
    {
        "mmsi": "367112233",
        "name": "KAHUKU TRADER",
        "type": "Inter-Island Cargo",
        "lat": 19.8500,
        "lon": -155.0500,
        "sog": 10.2,
        "cog": 170.0,
        "nav_status": "Under way using engine",
        "destination": "HILO HARBOR",
        "flag": "United States",
        "length_m": 115
    }
]

class AISVesselAdapter(BaseProviderAdapter):
    source_id = "global-ais-maritime"
    category = "vessel"
    name = "Global Maritime AIS Stream"

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        now_utc = datetime.now(timezone.utc)
        signals: List[SignalEnvelope] = []

        for rec in VESSEL_RECORDS:
            lon, lat = validate_coordinates(rec["lon"], rec["lat"])
            if bbox and not is_point_in_bbox(lon, lat, bbox):
                continue

            raw_hash = compute_record_hash(rec)
            signal = SignalEnvelope(
                id=f"vessel-{rec['mmsi']}",
                sourceId=self.source_id,
                sourceRecordId=rec["mmsi"],
                category=SignalCategory.VESSEL,
                signalType="ais-vessel-position",
                geometry=GeoJSONGeometry(
                    type=GeometryType.POINT,
                    coordinates=[lon, lat]
                ),
                latitude=lat,
                longitude=lon,
                observedAt=now_utc,
                publishedAt=now_utc,
                ingestedAt=now_utc,
                dataStatus=DataStatus.SIMULATED,  # curated sample, not fetched from the provider
                isSimulated=True,
                sourceUrl="https://www.navcen.uscg.gov/maritime-safety-information",
                source=SourceAttributionRef(
                    id=self.source_id,
                    name=self.name,
                    recordUrl="https://www.navcen.uscg.gov/",
                    attribution="[CURATED SAMPLE] Representative vessel profiles; not a live AIS feed"
                ),
                metadata={
                    "mmsi": rec["mmsi"],
                    "vesselName": rec["name"],
                    "vesselType": rec["type"],
                    "speedKnots": rec["sog"],
                    "courseDeg": rec["cog"],
                    "navStatus": rec["nav_status"],
                    "destination": rec["destination"],
                    "flag": rec["flag"],
                    "lengthMeters": rec["length_m"]
                },
                rawRecordHash=raw_hash,
                lastSeenAt=now_utc
            )
            signals.append(signal)

        self.last_sync_at = now_utc
        self.last_status = "simulated"
        return signals

    async def check_health(self) -> Dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "status": "healthy",
            "activeVessels": len(VESSEL_RECORDS),
            "lastSyncAt": self.last_sync_at,
            "isLive": False
        }

