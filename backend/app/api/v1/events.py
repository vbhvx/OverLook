# backend/app/api/v1/events.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_correlation
from backend.app.correlation.engine import CorrelationEngine
from backend.app.schemas.events import InvestigationEvent

router = APIRouter(prefix="/events", tags=["Events & Investigations"])


@router.get("", response_model=List[InvestigationEvent])
async def list_investigation_events(correlation: CorrelationEngine = Depends(get_correlation)):
    """
    Spatial-temporal investigation events. Every event states the rule that
    produced it, its measured criteria, and disclaims causal claims.
    """
    return await correlation.investigation_events()


@router.get("/{event_id}", response_model=InvestigationEvent)
async def get_investigation_event(event_id: str, correlation: CorrelationEngine = Depends(get_correlation)):
    """Full supporting records and matching criteria for one investigation event."""
    event = await correlation.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Investigation event '{event_id}' not found")
    return event
