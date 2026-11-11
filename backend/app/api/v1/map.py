# backend/app/api/v1/map.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_ingestion, get_store
from backend.app.ingestion.service import IngestionService
from backend.app.schemas.signals import MapSummaryResponse
from backend.app.storage.base import SignalStore

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/summary", response_model=MapSummaryResponse)
async def get_map_summary(
    store: SignalStore = Depends(get_store),
    ingestion: IngestionService = Depends(get_ingestion),
):
    """Global signal counts by category and data status, plus provider health."""
    categories = await store.count_by("category")
    statuses = await store.count_by("data_status")
    return MapSummaryResponse(
        activeSignalsCount=sum(categories.values()),
        categoryBreakdown=categories,
        statusBreakdown=statuses,
        sourceHealth={s.id: s.status for s in await ingestion.registry()},
        lastUpdated=datetime.now(timezone.utc),
    )
