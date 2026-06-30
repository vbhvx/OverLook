# backend/app/api/v1/health.py
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.ingestion.synchronizer import synchronizer

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=Dict[str, Any])
async def get_service_health():
    """Returns overall service health, uptime, provider readiness, and active signal count."""
    active_count = len(synchronizer._signals)
    sources_summary = {
        s_id: s_reg.status for s_id, s_reg in synchronizer.sources.items()
    }
    
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "activeSignals": active_count,
        "sources": sources_summary,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

