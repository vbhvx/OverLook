# backend/app/api/v1/sources.py
import math
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import get_ingestion, get_store
from backend.app.ingestion.service import IngestionService, SyncCooldownError, UnknownSourceError
from backend.app.schemas.sources import SourceRegistryItem, SourceSyncResult
from backend.app.storage.base import SignalStore

router = APIRouter(prefix="/sources", tags=["Sources"])


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
async def trigger_source_sync(source_id: str, ingestion: IngestionService = Depends(get_ingestion)):
    """Runs one ingestion cycle for a source now. Limited to one call per source per cooldown."""
    try:
        return await ingestion.sync_now(source_id)
    except UnknownSourceError:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' has no configured adapter") from None
    except SyncCooldownError as exc:
        retry = max(1, math.ceil(exc.retry_after))
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": str(retry)}) from None


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
