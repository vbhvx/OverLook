# backend/app/providers/osm_infrastructure.py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.providers.base import BaseProviderAdapter, compute_record_hash
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry,
    GeometryType, SourceAttributionRef
)
from backend.app.geospatial.validation import validate_coordinates, is_point_in_bbox

# Open geographic infrastructure landmarks & public transport nodes
INFRASTRUCTURE_NODES = [
    {
        "id": "osm-node-sfo-airport",
        "name": "San Francisco International Airport (SFO)",
        "facility_type": "international_airport",
        "lat": 37.6188,
        "lon": -122.3750,
        "operator": "City & County of San Francisco",
        "iata": "SFO",
        "icao": "KSFO",
        "osm_id": "relation/1066757"
    },
    {
        "id": "osm-node-port-of-oakland",
        "name": "Port of Oakland Maritime Terminals",
        "facility_type": "container_port",
        "lat": 37.7950,
        "lon": -122.3020,
        "operator": "Port of Oakland",
        "osm_id": "way/12345678"
    },
    {
        "id": "osm-node-golden-gate-bridge",
        "name": "Golden Gate Bridge",
        "facility_type": "suspension_bridge",
        "lat": 37.8199,
        "lon": -122.4783,
        "operator": "Golden Gate Bridge, Highway and Transportation District",
        "osm_id": "way/19488344"
    },
    {
        "id": "osm-node-bay-bridge",
        "name": "San Francisco-Oakland Bay Bridge",
        "facility_type": "bridge_corridor",
        "lat": 37.7983,
        "lon": -122.3778,
        "operator": "Caltrans",
        "osm_id": "way/23488219"
    },
    {
        "id": "osm-node-port-of-dover",
        "name": "Port of Dover Eastern Docks",
        "facility_type": "passenger_freight_ferry_port",
        "lat": 51.1280,
        "lon": 1.3350,
        "operator": "Dover Harbour Board",
        "osm_id": "relation/1283948"
    },
    {
        "id": "osm-node-port-of-singapore",
        "name": "PSA Singapore Jurong & Pasir Panjang Terminals",
        "facility_type": "container_mega_hub",
        "lat": 1.2700,
        "lon": 103.7700,
        "operator": "PSA Corporation Limited",
        "osm_id": "relation/948271"
    },
    {
        "id": "osm-node-tokyo-haneda",
        "name": "Tokyo Haneda International Airport (HND)",
        "facility_type": "international_airport",
        "lat": 35.5494,
        "lon": 139.7798,
        "operator": "Japan Civil Aviation Bureau",
        "iata": "HND",
        "osm_id": "relation/129482"
    },
    {
        "id": "osm-node-hvo-observatory",
        "name": "USGS Hawaiian Volcano Observatory & Seismic Array",
        "facility_type": "geophysical_observatory",
        "lat": 19.4200,
        "lon": -155.2900,
        "operator": "USGS Earthquake Hazards Program",
        "osm_id": "node/8492019"
    }
]

class OSMInfrastructureAdapter(BaseProviderAdapter):
    source_id = "osm-critical-infra"
    category = "infrastructure"
    name = "OpenStreetMap Public Infrastructure"

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        now_utc = datetime.now(timezone.utc)
        signals: List[SignalEnvelope] = []

        for node in INFRASTRUCTURE_NODES:
            lon, lat = validate_coordinates(node["lon"], node["lat"])
            if bbox and not is_point_in_bbox(lon, lat, bbox):
                continue

            raw_hash = compute_record_hash(node)

            signal = SignalEnvelope(
                id=f"infra-{node['id']}",
                sourceId=self.source_id,
                sourceRecordId=node["id"],
                category=SignalCategory.INFRASTRUCTURE,
                signalType=f"civil-infrastructure-{node['facility_type']}",
                geometry=GeoJSONGeometry(
                    type=GeometryType.POINT,
                    coordinates=[lon, lat]
                ),
                latitude=lat,
                longitude=lon,
                observedAt=now_utc,
                publishedAt=now_utc,
                ingestedAt=now_utc,
                dataStatus=DataStatus.ACTUAL,
                isSimulated=False,
                sourceUrl=f"https://www.openstreetmap.org/{node.get('osm_id', '')}",
                source=SourceAttributionRef(
                    id=self.source_id,
                    name=self.name,
                    recordUrl="https://www.openstreetmap.org/",
                    attribution="© OpenStreetMap contributors under Open Database License (ODbL)"
                ),
                metadata={
                    "facilityName": node["name"],
                    "facilityType": node["facility_type"],
                    "operatingEntity": node["operator"],
                    "osmReference": node.get("osm_id"),
                    "iataCode": node.get("iata"),
                    "icaoCode": node.get("icao"),
                    "safetyContext": (
                        "Public civil infrastructure context only. "
                        "No non-public access routes or sensitive vulnerability details are modeled."
                    )
                },
                rawRecordHash=raw_hash,
                lastSeenAt=now_utc
            )
            signals.append(signal)

        self.last_sync_at = now_utc
        self.last_status = "active"
        return signals

    async def check_health(self) -> Dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "status": "healthy",
            "registeredFacilities": len(INFRASTRUCTURE_NODES),
            "lastSyncAt": self.last_sync_at,
            "isLive": False
        }

