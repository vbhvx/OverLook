# backend/app/api/v1/regions.py
from typing import List

from fastapi import APIRouter

from backend.app.geospatial.regions import SYSTEM_REGIONS
from backend.app.schemas.sources import SavedRegion

router = APIRouter(prefix="/regions", tags=["Regions"])


@router.get("", response_model=List[SavedRegion])
async def list_analytical_regions():
    """Lists predefined geographic regions for rapid situational assessment and camera jumps."""
    return SYSTEM_REGIONS
