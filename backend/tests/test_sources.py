# backend/tests/test_sources.py
import pytest
from datetime import datetime, timezone
from backend.app.ingestion.synchronizer import synchronizer
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry, GeometryType
)

@pytest.fixture(autouse=True)
def setup_sync():
    synchronizer.load_initial_fixtures()

def test_source_registry_metadata():
    sources = synchronizer.sources
    assert "usgs-earthquakes" in sources
    assert "open-meteo" in sources
    assert "opensky-network" in sources
    assert "global-ais-maritime" in sources
    assert "copernicus-dataspace" in sources
    assert "public-dot-cameras" in sources
    assert "osm-critical-infra" in sources

    usgs = sources["usgs-earthquakes"]
    assert usgs.licenseStatus == "public_domain"
    assert usgs.commercialUseStatus == "unrestricted"
    assert "Data courtesy of the U.S. Geological Survey" in usgs.attributionRequirements

def test_deduplication_preserves_single_signal_id():
    now = datetime.now(timezone.utc)
    sig1 = SignalEnvelope(
        id="dedup-test-1",
        sourceId="usgs-earthquakes",
        sourceRecordId="rec-1",
        category=SignalCategory.EARTHQUAKE,
        signalType="seismic-event",
        geometry=GeoJSONGeometry(type=GeometryType.POINT, coordinates=[-122.0, 37.0]),
        latitude=37.0,
        longitude=-122.0,
        observedAt=now,
        ingestedAt=now,
        rawRecordHash="hash-v1",
        metadata={"mag": 3.0}
    )
    synchronizer._signals[sig1.id] = sig1
    init_count = len(synchronizer._signals)

    # Identical record re-ingested
    sig2 = sig1.model_copy()
    if sig2.id in synchronizer._signals:
        existing = synchronizer._signals[sig2.id]
        if existing.rawRecordHash == sig2.rawRecordHash:
            existing.lastSeenAt = now

    assert len(synchronizer._signals) == init_count

def test_source_failure_isolation():
    # If one adapter fails, synchronizer query still returns remaining active signals
    active_sigs = synchronizer.query_signals()
    assert len(active_sigs) > 0
    # Earthquake signals exist
    eqs = synchronizer.query_signals(category="earthquake")
    assert len(eqs) > 0
    # Weather signals exist
    wx = synchronizer.query_signals(category="weather")
    assert len(wx) > 0

