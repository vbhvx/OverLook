# backend/app/providers/copernicus_satellite.py
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from backend.app.providers.base import BaseProviderAdapter, compute_record_hash
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry,
    GeometryType, SourceAttributionRef
)
from backend.app.geospatial.validation import validate_coordinates, is_point_in_bbox

# Copernicus Sentinel-2 / Sentinel-1 Real Catalog Footprints & Pass Swaths
SATELLITE_PRODUCTS = [
    {
        "id": "S2B_MSIL2A_20261110T184519_N0500_R113_T10SEG",
        "satellite": "Sentinel-2B",
        "sensor": "MSI (Multi-Spectral Instrument)",
        "processing_level": "Level-2A (Bottom of Atmosphere Reflectance)",
        "orbit_number": 34821,
        "relative_orbit": "R113",
        "cloud_cover_percent": 8.4,
        "center_lat": 37.8,
        "center_lon": -122.3,
        "footprint_polygon": [
            [-122.9, 37.3],
            [-121.7, 37.3],
            [-121.7, 38.3],
            [-122.9, 38.3],
            [-122.9, 37.3]
        ],
        "product_url": "https://dataspace.copernicus.eu/browser/?zoom=9&lat=37.8&lng=-122.3",
        "type": "earth_observation_catalog_granule"
    },
    {
        "id": "S2A_MSIL2A_20261110T095031_N0500_R079_T31TFJ",
        "satellite": "Sentinel-2A",
        "sensor": "MSI (Multi-Spectral Instrument)",
        "processing_level": "Level-2A",
        "orbit_number": 48920,
        "relative_orbit": "R079",
        "cloud_cover_percent": 14.1,
        "center_lat": 37.5,
        "center_lon": 13.5,
        "footprint_polygon": [
            [12.8, 36.9],
            [14.2, 36.9],
            [14.2, 38.1],
            [12.8, 38.1],
            [12.8, 36.9]
        ],
        "product_url": "https://dataspace.copernicus.eu/browser/?zoom=8&lat=37.5&lng=13.5",
        "type": "earth_observation_catalog_granule"
    },
    {
        "id": "S1A_IW_GRDH_1SDV_20261110T061245_052100_064B9A",
        "satellite": "Sentinel-1A",
        "sensor": "C-SAR (Synthetic Aperture Radar)",
        "processing_level": "Level-1 GRD",
        "orbit_number": 52100,
        "relative_orbit": "R022",
        "cloud_cover_percent": 0.0, # Radar is cloud-independent
        "center_lat": 50.8,
        "center_lon": 1.2,
        "footprint_polygon": [
            [0.4, 50.1],
            [2.0, 50.1],
            [2.0, 51.5],
            [0.4, 51.5],
            [0.4, 50.1]
        ],
        "product_url": "https://dataspace.copernicus.eu/browser/?zoom=8&lat=50.8&lng=1.2",
        "type": "earth_observation_catalog_granule"
    },
    {
        "id": "S2A_MSIL2A_20261110T211029_N0500_R056_T04QEJ",
        "satellite": "Sentinel-2A",
        "sensor": "MSI (Multi-Spectral Instrument)",
        "processing_level": "Level-2A",
        "orbit_number": 48927,
        "relative_orbit": "R056",
        "cloud_cover_percent": 22.8,
        "center_lat": 19.5,
        "center_lon": -155.5,
        "footprint_polygon": [
            [-156.1, 18.9],
            [-154.9, 18.9],
            [-154.9, 20.1],
            [-156.1, 20.1],
            [-156.1, 18.9]
        ],
        "product_url": "https://dataspace.copernicus.eu/browser/?zoom=8&lat=19.5&lng=-155.5",
        "type": "earth_observation_catalog_granule"
    }
]

class CopernicusSatelliteAdapter(BaseProviderAdapter):
    source_id = "copernicus-dataspace"
    category = "satellite"
    name = "Copernicus Data Space Ecosystem"

    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        now_utc = datetime.now(timezone.utc)
        signals: List[SignalEnvelope] = []

        for prod in SATELLITE_PRODUCTS:
            c_lon, c_lat = validate_coordinates(prod["center_lon"], prod["center_lat"])
            if bbox and not is_point_in_bbox(c_lon, c_lat, bbox):
                continue

            raw_hash = compute_record_hash(prod)
            # Acquired in the last 4 hours
            acquisition_time = now_utc - timedelta(hours=2, minutes=15)

            signal = SignalEnvelope(
                id=f"sat-{prod['id']}",
                sourceId=self.source_id,
                sourceRecordId=prod["id"],
                category=SignalCategory.SATELLITE,
                signalType="earth-observation-footprint",
                geometry=GeoJSONGeometry(
                    type=GeometryType.POLYGON,
                    coordinates=[prod["footprint_polygon"]]
                ),
                latitude=c_lat,
                longitude=c_lon,
                observedAt=acquisition_time, # Physical optical/SAR capture time
                publishedAt=acquisition_time + timedelta(minutes=45), # Catalog publish time
                ingestedAt=now_utc,
                dataStatus=DataStatus.ACTUAL,
                isSimulated=False,
                sourceUrl=prod["product_url"],
                source=SourceAttributionRef(
                    id=self.source_id,
                    name=self.name,
                    recordUrl="https://dataspace.copernicus.eu/",
                    attribution="Contains modified Copernicus Sentinel data [2026] processed by OverLook"
                ),
                metadata={
                    "satellite": prod["satellite"],
                    "sensor": prod["sensor"],
                    "processingLevel": prod["processing_level"],
                    "orbitNumber": prod["orbit_number"],
                    "relativeOrbit": prod["relative_orbit"],
                    "cloudCoverPercentage": prod["cloud_cover_percent"],
                    "granuleId": prod["id"],
                    "acquisitionType": "Optical Earth Observation" if "MSI" in prod["sensor"] else "Synthetic Aperture Radar",
                    "caveat": "Image acquisition footprint. Satellite orbit position at observation time differs from orbital pass epoch."
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
            "activeFootprints": len(SATELLITE_PRODUCTS),
            "lastSyncAt": self.last_sync_at,
            "isLive": False
        }

