# backend/app/schemas/signals.py
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import math

class SignalCategory(str, Enum):
    AIRCRAFT = "aircraft"
    VESSEL = "vessel"
    SATELLITE = "satellite"
    EARTHQUAKE = "earthquake"
    WEATHER = "weather"
    CAMERA = "camera"
    INFRASTRUCTURE = "infrastructure"

class DataStatus(str, Enum):
    ACTUAL = "actual"
    FORECAST = "forecast"
    STALE = "stale"
    DELAYED = "delayed"
    SIMULATED = "simulated"
    QUARANTINED = "quarantined"

class GeometryType(str, Enum):
    POINT = "Point"
    POLYGON = "Polygon"
    LINESTRING = "LineString"
    MULTIPOINT = "MultiPoint"

class GeoJSONGeometry(BaseModel):
    type: GeometryType
    # Point: [lon, lat] or [lon, lat, alt]
    # Polygon: [[[lon, lat], ...]]
    coordinates: Union[List[float], List[List[List[float]]], List[List[float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_coord_ranges(cls, v, info):
        # Validate ranges for simple point
        if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], (int, float)) and isinstance(v[1], (int, float)):
            lon, lat = float(v[0]), float(v[1])
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Longitude {lon} out of range [-180, 180]")
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude {lat} out of range [-90, 90]")
        return v

class SourceAttributionRef(BaseModel):
    id: str
    name: Optional[str] = None
    recordUrl: Optional[str] = None
    attribution: Optional[str] = None

class SignalEnvelope(BaseModel):
    id: str = Field(..., description="Unique internal signal identifier")
    sourceId: str = Field(..., description="Registered source identifier")
    sourceRecordId: Optional[str] = Field(None, description="Original source record identifier")
    category: SignalCategory
    signalType: str = Field(..., description="Specific signal classification")
    geometry: GeoJSONGeometry
    latitude: float
    longitude: float
    altitudeM: Optional[float] = None
    
    # Temporal normalization
    observedAt: datetime = Field(..., description="Timestamp of physical observation in UTC")
    publishedAt: Optional[datetime] = Field(None, description="Timestamp source published the record")
    ingestedAt: datetime = Field(..., description="Timestamp record was ingested by OverLook")
    validFrom: Optional[datetime] = Field(None, description="Start of validity interval")
    validUntil: Optional[datetime] = Field(None, description="End of validity interval")
    
    # Quality & Provenance
    dataStatus: DataStatus = Field(DataStatus.ACTUAL, description="Data state")
    isSimulated: bool = Field(False, description="Flag indicating simulated demonstration fixture")
    sourceUrl: Optional[str] = Field(None, description="URL of source record or provider portal")
    source: Optional[SourceAttributionRef] = None
    
    # Category-specific normalized attributes
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Audit & Tracking
    rawRecordHash: Optional[str] = None
    schemaVersion: str = "1.0.0"
    lastSeenAt: Optional[datetime] = None

class SignalQueryResponse(BaseModel):
    items: List[SignalEnvelope]
    total: int
    meta: Dict[str, Any] = Field(default_factory=dict)

class TimelineBucket(BaseModel):
    bucketTime: datetime
    categoryCounts: Dict[str, int]
    totalCount: int

class TimelineResponse(BaseModel):
    interval: str
    startTime: datetime
    endTime: datetime
    buckets: List[TimelineBucket]
    totalSignals: int

class MapSummaryResponse(BaseModel):
    activeSignalsCount: int
    categoryBreakdown: Dict[str, int]
    statusBreakdown: Dict[str, int]
    sourceHealth: Dict[str, str]
    lastUpdated: datetime

