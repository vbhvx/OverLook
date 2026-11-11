# backend/app/api/v1/sources.py
import math
import time
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import get_ingestion, get_settings, get_store
from backend.app.config import Settings
from backend.app.ingestion.service import IngestionService
from backend.app.schemas.sources import SourceRegistryItem, SourceSyncResult
from backend.app.storage.base import SignalStore

router = APIRouter(prefix="/sources", tags=["Sources"])

# Manual sync spends a provider's rate budget, so it is throttled per source.
_last_manual_sync: Dict[str, float] = {}


@router.get("", response_model=List[SourceRegistryItem])
async def list_registered_sources(ingestion: IngestionService = Depends(get_ingestion)):
    """Registered providers with license terms, capabilities, live health and record counts."""
    return await ingestion.registry()


@router.get("/{source_id}", response_model=SourceRegistryItem)
async def get_source(source_id: str, ingestion: IngestionService = Depends(get_ingestion)):
    for item in await ingestion.registry():
        if item.id == source_id:
            return item
    raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found in registry")


@router.post("/{source_id}/sync", response_model=SourceSyncResult)
async def trigger_source_sync(
    source_id: str,
    ingestion: IngestionService = Depends(get_ingestion),
    settings: Settings = Depends(get_settings),
):
    """Runs one ingestion cycle for a source now. Limited to one call per source per cooldown."""
    if source_id not in ingestion.adapters:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' has no configured adapter")

    now = time.monotonic()
    elapsed = now - _last_manual_sync.get(source_id, -math.inf)
    if elapsed < settings.MANUAL_SYNC_COOLDOWN_SECONDS:
        retry = math.ceil(settings.MANUAL_SYNC_COOLDOWN_SECONDS - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"Source '{source_id}' was synced recently; retry in {retry}s",
            headers={"Retry-After": str(retry)},
        )
    _last_manual_sync[source_id] = now
    return await ingestion.sync_source(source_id)


@router.get("/{source_id}/runs", response_model=List[SourceSyncResult])
async def get_source_sync_runs(
    source_id: str,
    limit: int = Query(10, ge=1, le=50),
    ingestion: IngestionService = Depends(get_ingestion),
    store: SignalStore = Depends(get_store),
):
    """Recent sync runs for a source, newest first."""
    if source_id not in ingestion.adapters:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found in registry")
    return await store.list_sync_runs(source_id, limit)
