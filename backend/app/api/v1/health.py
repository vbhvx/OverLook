# backend/app/api/v1/health.py
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.app.api.deps import get_ingestion, get_settings, get_store
from backend.app.config import Settings
from backend.app.ingestion.service import IngestionService
from backend.app.storage.base import SignalStore

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness():
    """The process is up. Never touches dependencies, so a DB outage doesn't trigger restarts."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(store: SignalStore = Depends(get_store)):
    """Ready to serve traffic: the store answers. Load balancers route on this."""
    if await store.ping():
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "unavailable", "reason": "store unreachable"})


@router.get("", response_model=Dict[str, Any])
async def get_service_health(
    store: SignalStore = Depends(get_store),
    ingestion: IngestionService = Depends(get_ingestion),
    settings: Settings = Depends(get_settings),
):
    """Human-oriented summary: store reachability, provider statuses and signal count."""
    store_ok = await store.ping()
    sources: Dict[str, str] = {}
    active = 0
    if store_ok:
        try:
            registry = await ingestion.registry()
            sources = {s.id: s.status for s in registry}
            active = sum(s.activeRecordCount for s in registry)
        except Exception:
            # A health endpoint reports failure; it must not become one.
            store_ok = False
    degraded = [sid for sid, st in sources.items() if st in ("degraded", "rate_limited", "offline")]

    if not store_ok:
        status = "unhealthy"
    elif degraded:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "store": "postgis" if settings.uses_postgis else "memory",
        "storeReachable": store_ok,
        "activeSignals": active,
        "degradedSources": degraded,
        "sources": sources,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
