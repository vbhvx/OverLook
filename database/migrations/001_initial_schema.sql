-- 001_initial_schema.sql
-- OverLook: Public Signal Intelligence & Situational Awareness Platform
-- PostgreSQL + PostGIS Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- 1. Source Provider Registry
CREATE TABLE IF NOT EXISTS sources (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    provider_type VARCHAR(64) NOT NULL,
    official_docs_url VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- active, degraded, rate_limited, disabled, simulated
    license_status VARCHAR(64) NOT NULL,
    commercial_use_status VARCHAR(64) NOT NULL,
    attribution_requirements TEXT,
    supported_capabilities JSONB DEFAULT '[]'::jsonb,
    refresh_policy VARCHAR(64) NOT NULL DEFAULT 'polling', -- polling, event_driven, manual
    rate_limit_policy JSONB DEFAULT '{}'::jsonb,
    last_success_at TIMESTAMPTZ,
    last_error_at TIMESTAMPTZ,
    last_error_message TEXT,
    disabled_reason TEXT,
    is_live BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Ingestion & Synchronization Run History
CREATE TABLE IF NOT EXISTS source_sync_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(64) REFERENCES sources(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL, -- running, success, partial, failed
    records_fetched INT NOT NULL DEFAULT 0,
    records_ingested INT NOT NULL DEFAULT 0,
    records_updated INT NOT NULL DEFAULT 0,
    records_rejected INT NOT NULL DEFAULT 0,
    error_message TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sync_runs_source_started ON source_sync_runs(source_id, started_at DESC);

-- 3. Raw Source Record Provenance & Fingerprints
CREATE TABLE IF NOT EXISTS source_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(64) REFERENCES sources(id) ON DELETE CASCADE,
    external_record_id VARCHAR(255) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    source_published_at TIMESTAMPTZ,
    source_observed_at TIMESTAMPTZ,
    source_updated_at TIMESTAMPTZ,
    source_version VARCHAR(32),
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_status VARCHAR(32) NOT NULL DEFAULT 'processed',
    validation_errors JSONB,
    CONSTRAINT uq_source_record UNIQUE (source_id, external_record_id)
);
CREATE INDEX IF NOT EXISTS idx_source_records_hash ON source_records(record_hash);

-- 4. Common Normalized Signals
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(128) PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    source_record_id UUID REFERENCES source_records(id) ON DELETE SET NULL,
    category VARCHAR(64) NOT NULL,
    signal_type VARCHAR(64) NOT NULL,
    geom GEOMETRY(Geometry, 4326),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    altitude_m DOUBLE PRECISION,
    observed_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    data_status VARCHAR(32) NOT NULL DEFAULT 'actual', -- actual, forecast, stale, delayed, simulated, quarantined
    source_url VARCHAR(1024),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    is_simulated BOOLEAN NOT NULL DEFAULT false,
    raw_record_hash VARCHAR(64),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Spatial and B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_signals_geom ON signals USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_signals_category ON signals(category);
CREATE INDEX IF NOT EXISTS idx_signals_observed_at ON signals(observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source_id);
CREATE INDEX IF NOT EXISTS idx_signals_data_status ON signals(data_status);
CREATE INDEX IF NOT EXISTS idx_signals_composite_query ON signals(category, observed_at DESC, data_status);

-- 5. Time-Series Signal Positions
CREATE TABLE IF NOT EXISTS signal_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id VARCHAR(128) REFERENCES signals(id) ON DELETE CASCADE,
    source_id VARCHAR(64) REFERENCES sources(id) ON DELETE CASCADE,
    geom GEOMETRY(Point, 4326) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    altitude_m DOUBLE PRECISION,
    heading_deg DOUBLE PRECISION,
    speed_knots DOUBLE PRECISION,
    position_timestamp TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    position_quality VARCHAR(32),
    accuracy_metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_signal_position UNIQUE (signal_id, position_timestamp)
);
CREATE INDEX IF NOT EXISTS idx_signal_positions_geom ON signal_positions USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_signal_positions_timestamp ON signal_positions(signal_id, position_timestamp DESC);

-- 6. Signal Events and Revisions
CREATE TABLE IF NOT EXISTS signal_events (
    id VARCHAR(128) PRIMARY KEY,
    source_id VARCHAR(64) REFERENCES sources(id) ON DELETE CASCADE,
    external_event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    geom GEOMETRY(Geometry, 4326),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    occurred_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'published', -- published, reviewed, superseded, retracted
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_url VARCHAR(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_source_event UNIQUE (source_id, external_event_id)
);
CREATE INDEX IF NOT EXISTS idx_signal_events_geom ON signal_events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_signal_events_occurred_at ON signal_events(occurred_at DESC);

-- 7. Cross-Source Signal Associations & Correlation Explanations
CREATE TABLE IF NOT EXISTS signal_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    left_signal_id VARCHAR(128) REFERENCES signals(id) ON DELETE CASCADE,
    right_signal_id VARCHAR(128) REFERENCES signals(id) ON DELETE CASCADE,
    relation_type VARCHAR(64) NOT NULL, -- spatial_proximity, temporal_overlap, co_located_alert
    rule_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    distance_km DOUBLE PRECISION,
    time_delta_seconds BIGINT,
    spatial_criteria JSONB NOT NULL,
    temporal_criteria JSONB NOT NULL,
    evidence_metadata JSONB DEFAULT '{}'::jsonb,
    hypothesis_disclaimer TEXT NOT NULL DEFAULT 'Proximity does not imply causation. This association represents spatial-temporal co-occurrence for analytical review.',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_signal_pair UNIQUE (left_signal_id, right_signal_id, relation_type)
);
CREATE INDEX IF NOT EXISTS idx_signal_relations_left ON signal_relations(left_signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_relations_right ON signal_relations(right_signal_id);

-- 8. Map Layers Registry & Visual Specs
CREATE TABLE IF NOT EXISTS map_layers (
    id VARCHAR(64) PRIMARY KEY,
    category VARCHAR(64) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    description TEXT,
    source_id VARCHAR(64) REFERENCES sources(id) ON DELETE SET NULL,
    geometry_type VARCHAR(32) NOT NULL DEFAULT 'Point',
    is_enabled_default BOOLEAN NOT NULL DEFAULT true,
    min_zoom INT NOT NULL DEFAULT 0,
    max_zoom INT NOT NULL DEFAULT 22,
    refresh_interval_sec INT NOT NULL DEFAULT 60,
    style_spec JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. Saved Analytical Regions
CREATE TABLE IF NOT EXISTS saved_regions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    bbox_west DOUBLE PRECISION NOT NULL,
    bbox_south DOUBLE PRECISION NOT NULL,
    bbox_east DOUBLE PRECISION NOT NULL,
    bbox_north DOUBLE PRECISION NOT NULL,
    center_latitude DOUBLE PRECISION NOT NULL,
    center_longitude DOUBLE PRECISION NOT NULL,
    zoom_level DOUBLE PRECISION NOT NULL DEFAULT 10.0,
    is_system_preset BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Saved Views
CREATE TABLE IF NOT EXISTS saved_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    region_id VARCHAR(64) REFERENCES saved_regions(id) ON DELETE SET NULL,
    active_layers JSONB NOT NULL DEFAULT '[]'::jsonb,
    time_range_start TIMESTAMPTZ,
    time_range_end TIMESTAMPTZ,
    data_status_filter JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Audit Events
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. Data Quality & Reconciliation Events
CREATE TABLE IF NOT EXISTS data_quality_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(64) REFERENCES sources(id) ON DELETE CASCADE,
    issue_type VARCHAR(64) NOT NULL, -- invalid_coordinates, missing_timestamp, rate_limited, schema_mismatch
    severity VARCHAR(32) NOT NULL DEFAULT 'warning', -- info, warning, error, critical
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

