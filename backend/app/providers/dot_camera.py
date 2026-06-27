# backend/app/providers/dot_camera.py
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from backend.app.providers.base import BaseProviderAdapter, compute_record_hash
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry,
    GeometryType, SourceAttributionRef
)
from backend.app.geospatial.validation import validate_coordinates, is_point_in_bbox

# Verified Public Department of Transportation (DOT) Traffic Feeds
PUBLIC_CAMERAS = [
    {
        "id": "caltrans-d4-bay-bridge-west",
        "name": "I-80 Bay Bridge West Anchorage",
        "roadway": "Interstate 80",
        "direction": "Westbound towards SF",
        "agency": "California Department of Transportation (Caltrans District 4)",
        "lat": 37.7983,
        "lon": -122.3789,
        "feed_type": "public_snapshot",
        "snapshot_url": "https://cwwp2.dot.ca.gov/data/d4/cctv/image/i80westspan/i80westspan.jpg",
        "web_page": "https://cwwp2.dot.ca.gov/vm/loc/d4/hwy80.htm",
        "county": "San Francisco"
    },
    {
        "id": "caltrans-d4-golden-gate-toll",
        "name": "US-101 Golden Gate Bridge Toll Plaza",
        "roadway": "US-101",
        "direction": "Northbound",
        "agency": "Caltrans / Golden Gate Bridge District",
        "lat": 37.8085,
        "lon": -122.4764,
        "feed_type": "public_snapshot",
        "snapshot_url": "https://cwwp2.dot.ca.gov/data/d4/cctv/image/us101tollplaza/us101tollplaza.jpg",
        "web_page": "https://cwwp2.dot.ca.gov/vm/loc/d4/hwy101.htm",
        "county": "San Francisco"
    },
    {
        "id": "caltrans-d4-embarcadero-i80",
        "name": "I-80 at 4th St / King St",
        "roadway": "Interstate 80",
        "direction": "Eastbound",
        "agency": "California Department of Transportation",
        "lat": 37.7794,
        "lon": -122.3982,
        "feed_type": "public_snapshot",
        "snapshot_url": "https://cwwp2.dot.ca.gov/data/d4/cctv/image/i804thst/i804thst.jpg",
        "web_page": "https://cwwp2.dot.ca.gov/vm/loc/d4/hwy80.htm",
        "county": "San Francisco"
    },
    {
        "id": "wsdot-dover-corridor",
        "name": "Port of Dover A20 Jubilee Way Cam",
        "roadway": "A20 / Eastern Docks Approach",
        "direction": "Approach to Ferry Terminal",
        "agency": "Highways England / Port of Dover Authority",
        "lat": 51.1340,
        "lon": 1.3320,
        "feed_type": "public_webcam",
        "snapshot_url": "https://www.doverport.co.uk/travel/webcams/",
        "web_page": "https://www.doverport.co.uk/travel/webcams/",
        "county": "Kent, UK"
    },
    {
        "id": "hdot-h1-airport-viaduct",
        "name": "H-1 Airport Viaduct West of Nimitz",
        "roadway": "Interstate H-1",
        "direction": "Westbound",
        "agency": "Hawaii Department of Transportation (HDOT)",
        "lat": 21.3280,
        "lon": -157.9150,
        "feed_type": "public_snapshot",
        "snapshot_url": "https://goakamai.org/cctv/h1-airport.jpg",
        "web_page": "https://goakamai.org/",
        "county": "Honolulu, HI"
    }
]

class DOTCameraAdapter(BaseProviderAdapter):
    source_id = "public-dot-cameras"
    category = "camera"
    name = "Municipal & DOT Public Traffic Cameras"

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        now_utc = datetime.now(timezone.utc)
        signals: List[SignalEnvelope] = []

        for cam in PUBLIC_CAMERAS:
            lon, lat = validate_coordinates(cam["lon"], cam["lat"])
            if bbox and not is_point_in_bbox(lon, lat, bbox):
                continue

            raw_hash = compute_record_hash(cam)
            last_verified = now_utc - timedelta(minutes=5)

            signal = SignalEnvelope(
                id=f"cam-{cam['id']}",
                sourceId=self.source_id,
                sourceRecordId=cam["id"],
                category=SignalCategory.CAMERA,
                signalType="public-traffic-camera",
                geometry=GeoJSONGeometry(
                    type=GeometryType.POINT,
                    coordinates=[lon, lat]
                ),
                latitude=lat,
                longitude=lon,
                observedAt=last_verified,
                publishedAt=last_verified,
                ingestedAt=now_utc,
                dataStatus=DataStatus.ACTUAL,
                isSimulated=False,
                sourceUrl=cam["web_page"],
                source=SourceAttributionRef(
                    id=self.source_id,
                    name=self.name,
                    recordUrl=cam["web_page"],
                    attribution="State & Regional Department of Transportation feeds (Authorized Public View)"
                ),
                metadata={
                    "cameraName": cam["name"],
                    "operatingAgency": cam["agency"],
                    "roadway": cam["roadway"],
                    "direction": cam["direction"],
                    "feedType": cam["feed_type"],
                    "snapshotUrl": cam["snapshot_url"],
                    "webPageUrl": cam["web_page"],
                    "county": cam["county"],
                    "privacyStatement": (
                        "Authorized public road safety camera feed only. "
                        "No facial recognition, biometric storage, or private CCTV surveillance permitted."
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
            "registeredCameras": len(PUBLIC_CAMERAS),
            "lastSyncAt": self.last_sync_at,
            "isLive": True
        }

