# backend/app/api/v1/sources.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from backend.app.schemas.sources import SourceRegistryItem, SourceSyncResult
from backend.app.ingestion.synchronizer import synchronizer

router = APIRouter(prefix="/sources", tags=["Sources"])

@router.get("", response_model=List[SourceRegistryItem])
async def list_registered_sources():
    """Lists all registered public intelligence providers, their license status, and capability states."""
    # Refresh active record counts
    for s_id, s_reg in synchronizer.sources.items():
        s_reg.activeRecordCount = sum(1 for s in synchronizer._signals.values() if s.sourceId == s_id)
    return list(synchronizer.sources.values())

@router.get("/{source_id}", response_model=SourceRegistryItem)
async def get_source(source_id: str):
    """Retrieves source specification and health for a single provider."""
    src = synchronizer.sources.get(source_id)
    if not src:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found in registry")
    src.activeRecordCount = sum(1 for s in synchronizer._signals.values() if s.sourceId == source_id)
    return src

@router.post("/{source_id}/sync", response_model=SourceSyncResult)
async def trigger_source_sync(source_id: str):
    """Manually triggers an ingestion and normalization cycle for a specific source."""
    if source_id not in synchronizer.adapters:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' has no configured adapter")
    result = await synchronizer.sync_source(source_id)
    return result

@router.get("/{source_id}/runs", response_model=List[SourceSyncResult])
async def get_source_sync_runs(source_id: str, limit: int = Query(10, ge=1, le=50)):
    """Retrieves recent sync runs and latency history for a source."""
    runs = [r for r in synchronizer.sync_runs if r.sourceId == source_id]
    return runs[-limit:]

