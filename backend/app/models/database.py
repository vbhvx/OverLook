# backend/app/models/database.py
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from backend.app.config import settings

Base = declarative_base()

class SourceModel(Base):
    __tablename__ = "sources"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    provider_type = Column(String(64), nullable=False)
    official_docs_url = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    license_status = Column(String(64), nullable=False)
    commercial_use_status = Column(String(64), nullable=False)
    attribution_requirements = Column(Text, nullable=True)
    supported_capabilities = Column(JSON, default=list)
    refresh_policy = Column(String(64), nullable=False, default="polling")
    rate_limit_policy = Column(JSON, default=dict)
    last_success_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    disabled_reason = Column(Text, nullable=True)
    is_live = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SourceSyncRunModel(Base):
    __tablename__ = "source_sync_runs"

    id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False)
    records_fetched = Column(Integer, default=0)
    records_ingested = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)

class SignalModel(Base):
    __tablename__ = "signals"

    id = Column(String(128), primary_key=True)
    source_id = Column(String(64), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    source_record_id = Column(String(255), nullable=True)
    category = Column(String(64), nullable=False, index=True)
    signal_type = Column(String(64), nullable=False)
    geometry_json = Column(JSON, nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    altitude_m = Column(Float, nullable=True)
    observed_at = Column(DateTime, nullable=False, index=True)
    published_at = Column(DateTime, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    data_status = Column(String(32), nullable=False, default="actual", index=True)
    source_url = Column(String(1024), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    schema_version = Column(String(16), default="1.0.0")
    is_simulated = Column(Boolean, default=False, nullable=False)
    raw_record_hash = Column(String(64), nullable=True, index=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MapLayerModel(Base):
    __tablename__ = "map_layers"

    id = Column(String(64), primary_key=True)
    category = Column(String(64), nullable=False)
    display_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    source_id = Column(String(64), nullable=True)
    geometry_type = Column(String(32), default="Point")
    is_enabled_default = Column(Boolean, default=True)
    min_zoom = Column(Integer, default=0)
    max_zoom = Column(Integer, default=22)
    refresh_interval_sec = Column(Integer, default=60)
    style_spec = Column(JSON, default=dict)

class SavedRegionModel(Base):
    __tablename__ = "saved_regions"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    bbox_west = Column(Float, nullable=False)
    bbox_south = Column(Float, nullable=False)
    bbox_east = Column(Float, nullable=False)
    bbox_north = Column(Float, nullable=False)
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    zoom_level = Column(Float, default=10.0)
    is_system_preset = Column(Boolean, default=False)

class SignalRelationModel(Base):
    __tablename__ = "signal_relations"

    id = Column(String(64), primary_key=True)
    left_signal_id = Column(String(128), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)
    right_signal_id = Column(String(128), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(64), nullable=False)
    rule_version = Column(String(32), default="1.0.0")
    distance_km = Column(Float, nullable=True)
    time_delta_seconds = Column(Integer, nullable=True)
    spatial_criteria = Column(JSON, nullable=False)
    temporal_criteria = Column(JSON, nullable=False)
    evidence_metadata = Column(JSON, default=dict)
    hypothesis_disclaimer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Engine and Session Setup
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

