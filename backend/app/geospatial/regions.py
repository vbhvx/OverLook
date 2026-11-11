# backend/app/geospatial/regions.py
"""Preset analytical regions, shared by the regions API and the correlation engine."""
from typing import List

from backend.app.schemas.sources import SavedRegion

SYSTEM_REGIONS: List[SavedRegion] = [
    SavedRegion(
        id="sf-bay",
        name="San Francisco Bay Area",
        description="High-density air, maritime, seismic, weather, and camera corridor in Northern California",
        bboxWest=-123.10,
        bboxSouth=37.20,
        bboxEast=-121.75,
        bboxNorth=38.30,
        centerLatitude=37.7749,
        centerLongitude=-122.4194,
        zoomLevel=9.5,
        isSystemPreset=True
    ),
    SavedRegion(
        id="hawaii-seismic",
        name="Hawaii Volcanic & Seismic Belt",
        description="Active seismic zone with USGS real-time monitoring and maritime routes",
        bboxWest=-156.50,
        bboxSouth=18.50,
        bboxEast=-154.50,
        bboxNorth=20.50,
        centerLatitude=19.45,
        centerLongitude=-155.50,
        zoomLevel=8.5,
        isSystemPreset=True
    ),
    SavedRegion(
        id="mediterranean-basin",
        name="Central Mediterranean",
        description="Major international maritime strait, seismic fault line, and cross-border airspace",
        bboxWest=9.50,
        bboxSouth=35.50,
        bboxEast=16.50,
        bboxNorth=39.50,
        centerLatitude=37.50,
        centerLongitude=13.50,
        zoomLevel=6.5,
        isSystemPreset=True
    ),
    SavedRegion(
        id="english-channel",
        name="English Channel & Dover Strait",
        description="Busiest shipping lane in the world connecting the North Sea to the Atlantic",
        bboxWest=-2.00,
        bboxSouth=49.50,
        bboxEast=2.00,
        bboxNorth=51.50,
        centerLatitude=50.50,
        centerLongitude=0.50,
        zoomLevel=8.0,
        isSystemPreset=True
    ),
    SavedRegion(
        id="tokyo-bay",
        name="Tokyo Bay & Kantō Plain",
        description="Major urban infrastructure, port logistics, and circum-Pacific seismic zone",
        bboxWest=139.20,
        bboxSouth=35.10,
        bboxEast=140.30,
        bboxNorth=35.90,
        centerLatitude=35.55,
        centerLongitude=139.78,
        zoomLevel=9.0,
        isSystemPreset=True
    ),
    SavedRegion(
        id="malacca-strait",
        name="Strait of Malacca",
        description="Strategic maritime choke-point between the Indian Ocean and South China Sea",
        bboxWest=98.00,
        bboxSouth=1.00,
        bboxEast=104.50,
        bboxNorth=4.50,
        centerLatitude=2.80,
        centerLongitude=101.50,
        zoomLevel=7.0,
        isSystemPreset=True
    )
]
