# backend/app/api/v1/layers.py
from typing import List, Dict, Any
from fastapi import APIRouter
from backend.app.schemas.sources import MapLayerSpec
from backend.app.ingestion.synchronizer import synchronizer

router = APIRouter(prefix="/layers", tags=["Layers"])

DEFAULT_LAYERS = [
    MapLayerSpec(
        id="layer-earthquakes",
        category="earthquake",
        displayName="Seismic Activity (USGS)",
        description="Global earthquake hypocenters, magnitudes, and revision updates from the USGS seismic network.",
        sourceId="usgs-earthquakes",
        geometryType="Point",
        isEnabledDefault=True,
        minZoom=0,
        maxZoom=22,
        refreshIntervalSec=60,
        styleSpec={
            "color": "#ef4444",
            "icon": "activity",
            "radiusProperty": "magnitude",
            "fillOpacity": 0.8
        }
    ),
    MapLayerSpec(
        id="layer-weather",
        category="weather",
        displayName="Atmospheric & Weather (Open-Meteo)",
        description="Real-time surface weather observations and short-term atmospheric forecasts.",
        sourceId="open-meteo",
        geometryType="Point",
        isEnabledDefault=True,
        minZoom=3,
        maxZoom=22,
        refreshIntervalSec=180,
        styleSpec={
            "color": "#06b6d4",
            "icon": "cloud-rain",
            "fillOpacity": 0.85
        }
    ),
    MapLayerSpec(
        id="layer-aircraft",
        category="aircraft",
        displayName="Air Traffic & State Vectors (OpenSky)",
        description="Public commercial and general aviation flights with barometric altitude and true heading.",
        sourceId="opensky-network",
        geometryType="Point",
        isEnabledDefault=True,
        minZoom=5,
        maxZoom=22,
        refreshIntervalSec=30,
        styleSpec={
            "color": "#3b82f6",
            "icon": "plane",
            "rotateWithHeading": True,
            "fillOpacity": 0.9
        }
    ),
    MapLayerSpec(
        id="layer-vessels",
        category="vessel",
        displayName="Maritime AIS Vessel Tracking",
        description="Authorized surface vessel positions, Speed Over Ground (SOG), and Course Over Ground (COG).",
        sourceId="global-ais-maritime",
        geometryType="Point",
        isEnabledDefault=True,
        minZoom=5,
        maxZoom=22,
        refreshIntervalSec=60,
        styleSpec={
            "color": "#10b981",
            "icon": "ship",
            "fillOpacity": 0.9
        }
    ),
    MapLayerSpec(
        id="layer-satellites",
        category="satellite",
        displayName="Earth Observation Passes (Copernicus)",
        description="Optical and radar imagery acquisition swaths and orbital sensor passes.",
        sourceId="copernicus-dataspace",
        geometryType="Polygon",
        isEnabledDefault=True,
        minZoom=1,
        maxZoom=14,
        refreshIntervalSec=300,
        styleSpec={
            "color": "#a855f7",
            "icon": "satellite",
            "fillOpacity": 0.2,
            "strokeWidth": 2
        }
    ),
    MapLayerSpec(
        id="layer-cameras",
        category="camera",
        displayName="Public DOT Traffic Cameras",
        description="Publicly authorized municipal and regional highway camera feeds and snapshots.",
        sourceId="public-dot-cameras",
        geometryType="Point",
        isEnabledDefault=False,
        minZoom=8,
        maxZoom=22,
        refreshIntervalSec=120,
        styleSpec={
            "color": "#f59e0b",
            "icon": "camera",
            "fillOpacity": 0.9
        }
    ),
    MapLayerSpec(
        id="layer-infrastructure",
        category="infrastructure",
        displayName="Public Critical Infrastructure (OSM)",
        description="Airports, international ports, bridges, and geophysical stations from open geospatial data.",
        sourceId="osm-critical-infra",
        geometryType="Point",
        isEnabledDefault=False,
        minZoom=4,
        maxZoom=22,
        refreshIntervalSec=600,
        styleSpec={
            "color": "#64748b",
            "icon": "building",
            "fillOpacity": 0.8
        }
    )
]

@router.get("", response_model=List[MapLayerSpec])
async def list_layers():
    """Lists available interactive map layers with active signal counts and display metadata."""
    layers: List[MapLayerSpec] = []
    for l_spec in DEFAULT_LAYERS:
        # Clone and enrich with active count and current source health
        active_count = sum(1 for s in synchronizer._signals.values() if s.category.value == l_spec.category)
        src = synchronizer.sources.get(l_spec.sourceId) if l_spec.sourceId else None
        
        enriched = l_spec.model_copy()
        enriched.activeCount = active_count
        enriched.sourceStatus = src.status if src else "active"
        layers.append(enriched)
        
    return layers

