# backend/app/api/v1/signals.py
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import get_correlation, get_settings, get_store
from backend.app.api.v1.params import as_utc, parse_bbox
from backend.app.config import Settings
from backend.app.correlation.engine import CorrelationEngine
from backend.app.schemas.signals import DataStatus, SignalCategory, SignalQueryResponse
from backend.app.storage.base import SignalQuery, SignalStore

router = APIRouter(prefix="/signals", tags=["Signals"])

DETAIL_RADIUS_KM = 60.0
DETAIL_WINDOW_HOURS = 6.0
DETAIL_MAX_RELATIONS = 6


@router.get("", response_model=SignalQueryResponse)
async def query_signals(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box 'west,south,east,north' (e.g. -123.5,37.0,-121.5,38.5). "
                    "west > east denotes a box crossing the antimeridian.",
    ),
    category: Optional[SignalCategory] = Query(None),
    source: Optional[str] = Query(None, description="Registered source ID"),
    data_status: Optional[DataStatus] = Query(None),
    start: Optional[datetime] = Query(None, description="Start observation time (ISO 8601; UTC if no offset)"),
    end: Optional[datetime] = Query(None, description="End observation time (ISO 8601; UTC if no offset)"),
    limit: int = Query(250, ge=1),
    offset: int = Query(0, ge=0, le=100_000),
    store: SignalStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    """
    Queries normalized signals by spatial viewport, time interval, category,
    source and data status. Ordered by observation time, newest first.
    """
    bbox_coords = parse_bbox(bbox)
    start, end = as_utc(start), as_utc(end)
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start must not be after end")
    limit = min(limit, settings.MAX_QUERY_RESULTS)

    items, total = await store.query_signals(SignalQuery(
        bbox=bbox_coords,
        category=category.value if category else None,
        source_id=source,
        data_status=data_status.value if data_status else None,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
    ))
    return SignalQueryResponse(
        items=items,
        total=total,
        meta={
            "limit": limit,
            "offset": offset,
            "count": len(items),
            "bboxApplied": bbox_coords is not None,
            "schemaVersion": "1.0.0",
        },
    )


@router.get("/{signal_id}", response_model=dict)
async def get_signal_detail(
    signal_id: str,
    store: SignalStore = Depends(get_store),
    correlation: CorrelationEngine = Depends(get_correlation),
):
    """Full normalized record, its provenance, and nearby cross-source observations."""
    sig = await store.get_signal(signal_id)
    if sig is None:
        raise HTTPException(status_code=404, detail=f"Signal with ID '{signal_id}' not found")

    relations, neighbors = await correlation.find_nearby_signals(
        sig, radius_km=DETAIL_RADIUS_KM, time_window_hours=DETAIL_WINDOW_HOURS, limit=DETAIL_MAX_RELATIONS
    )
    return {
        "signal": sig,
        "correlatedRelations": relations,
        "correlatedSignals": neighbors,
        "provenance": {
            "sourceId": sig.sourceId,
            "sourceUrl": sig.sourceUrl,
            "rawRecordHash": sig.rawRecordHash,
            "schemaVersion": sig.schemaVersion,
            "ingestedAt": sig.ingestedAt,
            "lastSeenAt": sig.lastSeenAt,
            "isSimulated": sig.isSimulated,
        },
    }
