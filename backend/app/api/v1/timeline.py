# backend/app/api/v1/timeline.py
from typing import Optional
from fastapi import APIRouter, Query
from backend.app.schemas.signals import TimelineResponse
from backend.app.ingestion.synchronizer import synchronizer

router = APIRouter(prefix="/timeline", tags=["Timeline"])

@router.get("", response_model=TimelineResponse)
async def get_timeline_histogram(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    interval_hours: int = Query(1, ge=1, le=24, description="Bucket interval size in hours"),
    category: Optional[str] = Query(None, description="Optional category filter")
):
    """
    Returns time-bucketed signal frequencies for timeline navigation and temporal distribution analysis.
    """
    return synchronizer.get_timeline(
        interval_hours=interval_hours,
        time_window_hours=hours,
        category=category
    )

