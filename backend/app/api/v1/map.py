# backend/app/api/v1/map.py
from fastapi import APIRouter
from backend.app.schemas.signals import MapSummaryResponse
from backend.app.ingestion.synchronizer import synchronizer

router = APIRouter(prefix="/map", tags=["Map"])

@router.get("/summary", response_model=MapSummaryResponse)
async def get_map_summary():
    """Returns global and viewport-level signal counts, category breakdowns, and provider statuses."""
    return synchronizer.get_map_summary()

