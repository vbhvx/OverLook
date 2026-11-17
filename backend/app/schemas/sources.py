# backend/app/schemas/sources.py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceRegistryItem(BaseModel):
    id: str
    name: str
    category: str
    providerType: str
    officialDocsUrl: Optional[str] = None
    status: str = "active" # active, degraded, rate_limited, disabled, simulated
    licenseStatus: str
    commercialUseStatus: str
    attributionRequirements: Optional[str] = None
    supportedCapabilities: List[str] = Field(default_factory=list)
    refreshPolicy: str = "polling"
    rateLimitPolicy: Dict[str, Any] = Field(default_factory=dict)
    lastSuccessAt: Optional[datetime] = None
    lastErrorAt: Optional[datetime] = None
    lastErrorMessage: Optional[str] = None
    disabledReason: Optional[str] = None
    isLive: bool = False
    activeRecordCount: int = 0

class SourceSyncResult(BaseModel):
    sourceId: str
    status: str
    recordsFetched: int
    recordsIngested: int
    recordsUpdated: int
    recordsRejected: int
    durationMs: int
    errorMessage: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MapLayerSpec(BaseModel):
    id: str
    category: str
    displayName: str
    description: Optional[str] = None
    sourceId: Optional[str] = None
    geometryType: str = "Point"
    isEnabledDefault: bool = True
    minZoom: int = 0
    maxZoom: int = 22
    refreshIntervalSec: int = 60
    styleSpec: Dict[str, Any] = Field(default_factory=dict)
    activeCount: int = 0
    sourceStatus: Optional[str] = "active"

class SavedRegion(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    bboxWest: float
    bboxSouth: float
    bboxEast: float
    bboxNorth: float
    centerLatitude: float
    centerLongitude: float
    zoomLevel: float = 10.0
    isSystemPreset: bool = False

