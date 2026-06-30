# backend/app/api/v1/signals.py
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.signals import (
    SignalEnvelope, SignalQueryResponse, SourceAttributionRef
)
from backend.app.schemas.events import SignalRelation
from backend.app.ingestion.synchronizer import synchronizer
from backend.app.correlation.engine import correlation_engine

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.get("", response_model=SignalQueryResponse)
async def query_signals(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in format 'west,south,east,north' (e.g. -123.5,37.0,-121.5,38.5)"
    ),
    category: Optional[str] = Query(None, description="aircraft, vessel, satellite, earthquake, weather, camera, infrastructure"),
    source: Optional[str] = Query(None, description="Registered source ID"),
    data_status: Optional[str] = Query(None, description="actual, forecast, stale, delayed, simulated, quarantined"),
    start: Optional[datetime] = Query(None, description="Start observation time (ISO 8601 UTC)"),
    end: Optional[datetime] = Query(None, description="End observation time (ISO 8601 UTC)"),
    limit: int = Query(250, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Queries normalized geospatial signals bounded by spatial viewport, time interval,
    category, source, and data status.
    """
    bbox_coords: Optional[List[float]] = None
    if bbox:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError()
            bbox_coords = parts
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid bbox format. Expected 'west,south,east,north' with numeric coordinates."
            )

    items = synchronizer.query_signals(
        bbox=bbox_coords,
        category=category,
        source_id=source,
        data_status=data_status,
        start_time=start,
        end_time=end,
        limit=limit,
        offset=offset
    )

    total_matching = len(synchronizer.query_signals(
        bbox=bbox_coords,
        category=category,
        source_id=source,
        data_status=data_status,
        start_time=start,
        end_time=end,
        limit=5000,
        offset=0
    ))

    return SignalQueryResponse(
        items=items,
        total=total_matching,
        meta={
            "limit": limit,
            "offset": offset,
            "count": len(items),
            "bboxApplied": bbox_coords is not None,
            "schemaVersion": "1.0.0"
        }
    )

@router.get("/{signal_id}", response_model=dict)
async def get_signal_detail(signal_id: str):
    """
    Retrieves full normalized signal record, original provenance, and nearby correlated signals.
    """
    sig = synchronizer.get_signal_by_id(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail=f"Signal with ID '{signal_id}' not found")

    # Find nearby cross-source associations
    relations = correlation_engine.find_nearby_signals(sig, radius_km=60.0, time_window_hours=6.0)
    
    # Retrieve neighbor records
    neighbor_signals: List[SignalEnvelope] = []
    for rel in relations[:6]:
        nb = synchronizer.get_signal_by_id(rel.rightSignalId)
        if nb:
            neighbor_signals.append(nb)

    return {
        "signal": sig,
        "correlatedRelations": relations[:6],
        "correlatedSignals": neighbor_signals,
        "provenance": {
            "sourceId": sig.sourceId,
            "sourceUrl": sig.sourceUrl,
            "rawRecordHash": sig.rawRecordHash,
            "schemaVersion": sig.schemaVersion,
            "ingestedAt": sig.ingestedAt,
            "lastSeenAt": sig.lastSeenAt,
            "isSimulated": sig.isSimulated
        }
    }

