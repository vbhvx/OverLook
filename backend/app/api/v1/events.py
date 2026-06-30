# backend/app/api/v1/events.py
from typing import List
from fastapi import APIRouter, HTTPException
from backend.app.schemas.events import InvestigationEvent
from backend.app.correlation.engine import correlation_engine

router = APIRouter(prefix="/events", tags=["Events & Investigations"])

@router.get("", response_model=List[InvestigationEvent])
async def list_investigation_events():
    """
    Returns high-interest spatial-temporal investigation events.
    Every event presents transparent criteria and disclaims causal claims.
    """
    return correlation_engine.build_investigation_events()

@router.get("/{event_id}", response_model=InvestigationEvent)
async def get_investigation_event(event_id: str):
    """Retrieves full supporting records and matching criteria for a specific investigation event."""
    events = correlation_engine.build_investigation_events()
    for ev in events:
        if ev.id == event_id:
            return ev
    raise HTTPException(status_code=404, detail=f"Investigation event '{event_id}' not found")

