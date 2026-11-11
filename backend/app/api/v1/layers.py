# backend/app/api/v1/layers.py
from typing import List

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_ingestion, get_store
from backend.app.ingestion.service import IngestionService
from backend.app.schemas.sources import MapLayerSpec
from backend.app.storage.base import SignalStore

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
async def list_layers(
    store: SignalStore = Depends(get_store),
    ingestion: IngestionService = Depends(get_ingestion),
):
    """Interactive map layers with active signal counts and current source health."""
    counts = await store.count_by("category")
    statuses = {s.id: s.status for s in await ingestion.registry()}
    return [
        spec.model_copy(update={
            "activeCount": counts.get(spec.category, 0),
            "sourceStatus": statuses.get(spec.sourceId, "active") if spec.sourceId else "active",
        })
        for spec in DEFAULT_LAYERS
    ]
