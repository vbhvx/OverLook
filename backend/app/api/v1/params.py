# backend/app/api/v1/params.py
"""Shared query-parameter parsing for v1 endpoints."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from backend.app.storage.base import BBox


def parse_bbox(raw: Optional[str]) -> Optional[BBox]:
    """'west,south,east,north' → tuple. west > east is allowed (antimeridian crossing)."""
    if raw is None:
        return None
    try:
        parts = [float(p.strip()) for p in raw.split(",")]
    except ValueError:
        parts = []
    if len(parts) != 4:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox format. Expected 'west,south,east,north' with numeric coordinates.",
        )
    west, south, east, north = parts
    if not all(-180.0 <= v <= 180.0 for v in (west, east)):
        raise HTTPException(status_code=400, detail="bbox longitudes must be within [-180, 180]")
    if not all(-90.0 <= v <= 90.0 for v in (south, north)):
        raise HTTPException(status_code=400, detail="bbox latitudes must be within [-90, 90]")
    if south > north:
        raise HTTPException(status_code=400, detail="bbox south must not exceed north")
    return west, south, east, north


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Timestamps without an offset are interpreted as UTC, per the API contract."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
