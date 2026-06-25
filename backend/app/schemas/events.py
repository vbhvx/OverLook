# backend/app/schemas/events.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.signals import SignalEnvelope

class SignalRelation(BaseModel):
    id: str
    leftSignalId: str
    rightSignalId: str
    relationType: str # spatial_proximity, temporal_overlap, co_located_alert
    ruleVersion: str = "1.0.0"
    distanceKm: Optional[float] = None
    timeDeltaSeconds: Optional[int] = None
    spatialCriteria: Dict[str, Any]
    temporalCriteria: Dict[str, Any]
    evidenceMetadata: Dict[str, Any] = Field(default_factory=dict)
    hypothesisDisclaimer: str = (
        "Proximity does not imply causation. This association represents "
        "spatial-temporal co-occurrence for analytical investigation."
    )
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class InvestigationEvent(BaseModel):
    id: str
    title: str
    category: str
    primarySignal: Optional[SignalEnvelope] = None
    correlatedSignals: List[SignalEnvelope] = Field(default_factory=list)
    relations: List[SignalRelation] = Field(default_factory=list)
    spatialBounds: Optional[Dict[str, float]] = None
    timeWindow: Dict[str, datetime]
    evidenceSummary: str
    confidenceLevel: str = "observational_association" # observational_association, validated_report
    ruleName: str
    disclaimer: str = (
        "Independent signals occurring within temporal and spatial proximity are "
        "correlated for situational awareness only. Do not assume causal dependency."
    )

