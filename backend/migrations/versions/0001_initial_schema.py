"""Initial schema: signals with spatial indexes, source health, sync history.

Revision ID: 0001
Revises:
Create Date: 2026-11-11
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.execute("""
        CREATE TABLE signals (
            id               TEXT PRIMARY KEY,
            source_id        TEXT        NOT NULL,
            category         TEXT        NOT NULL,
            data_status      TEXT        NOT NULL,
            is_simulated     BOOLEAN     NOT NULL DEFAULT false,
            observed_at      TIMESTAMPTZ NOT NULL,
            ingested_at      TIMESTAMPTZ NOT NULL,
            last_seen_at     TIMESTAMPTZ NOT NULL,
            raw_record_hash  TEXT,
            geom             geometry(Geometry, 4326) NOT NULL,
            point            geography(Point, 4326)   NOT NULL,
            payload          JSONB       NOT NULL,
            CONSTRAINT ck_signals_category CHECK (category IN (
                'aircraft', 'vessel', 'satellite', 'earthquake', 'weather', 'camera', 'infrastructure'
            )),
            CONSTRAINT ck_signals_data_status CHECK (data_status IN (
                'actual', 'forecast', 'stale', 'delayed', 'simulated', 'quarantined'
            ))
        )
    """)
    # Spatial: bbox intersection on real geometry, radius search on geography.
    op.execute("CREATE INDEX ix_signals_geom  ON signals USING GIST (geom)")
    op.execute("CREATE INDEX ix_signals_point ON signals USING GIST (point)")
    # Default listing order, and the common "one layer, newest first" query.
    op.execute("CREATE INDEX ix_signals_observed_at ON signals (observed_at DESC, id)")
    op.execute("CREATE INDEX ix_signals_category_observed ON signals (category, observed_at DESC)")
    op.execute("CREATE INDEX ix_signals_source ON signals (source_id)")
    # Retention sweep only ever touches live data.
    op.execute("CREATE INDEX ix_signals_live_last_seen ON signals (last_seen_at) WHERE NOT is_simulated")

    op.execute("""
        CREATE TABLE source_state (
            source_id            TEXT PRIMARY KEY,
            status               TEXT        NOT NULL,
            last_success_at      TIMESTAMPTZ,
            last_error_at        TIMESTAMPTZ,
            last_error_message   TEXT,
            consecutive_failures INTEGER     NOT NULL DEFAULT 0,
            circuit_state        TEXT        NOT NULL DEFAULT 'closed',
            extra                JSONB       NOT NULL DEFAULT '{}'::jsonb,
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE sync_runs (
            id               BIGSERIAL PRIMARY KEY,
            source_id        TEXT        NOT NULL,
            status           TEXT        NOT NULL,
            started_at       TIMESTAMPTZ NOT NULL,
            duration_ms      INTEGER     NOT NULL DEFAULT 0,
            records_fetched  INTEGER     NOT NULL DEFAULT 0,
            records_ingested INTEGER     NOT NULL DEFAULT 0,
            records_updated  INTEGER     NOT NULL DEFAULT 0,
            records_rejected INTEGER     NOT NULL DEFAULT 0,
            error_message    TEXT
        )
    """)
    op.execute("CREATE INDEX ix_sync_runs_source_started ON sync_runs (source_id, started_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sync_runs")
    op.execute("DROP TABLE IF EXISTS source_state")
    op.execute("DROP TABLE IF EXISTS signals")
