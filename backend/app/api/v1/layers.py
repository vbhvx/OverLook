# backend/app/api/v1/layers.py
from typing import List

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_ingestion, get_store
from backend.app.geospatial.layers import DEFAULT_LAYERS
from backend.app.ingestion.service import IngestionService
from backend.app.schemas.sources import MapLayerSpec
from backend.app.storage.base import SignalStore

router = APIRouter(prefix="/layers", tags=["Layers"])


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
