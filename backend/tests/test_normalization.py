# backend/tests/test_normalization.py
from datetime import datetime, timezone
import pytest
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry, GeometryType
)
from backend.app.ingestion.fixtures import get_simulated_fixtures

def test_signal_envelope_structure():
    now = datetime.now(timezone.utc)
    sig = SignalEnvelope(
        id="test-sig-1",
        sourceId="usgs-earthquakes",
        sourceRecordId="nc12345",
        category=SignalCategory.EARTHQUAKE,
        signalType="seismic-event",
        geometry=GeoJSONGeometry(type=GeometryType.POINT, coordinates=[-122.4, 37.7]),
        latitude=37.7,
        longitude=-122.4,
        observedAt=now,
        ingestedAt=now,
        dataStatus=DataStatus.ACTUAL,
        metadata={"magnitude": 4.2}
    )
    assert sig.id == "test-sig-1"
    assert sig.category == SignalCategory.EARTHQUAKE
    assert sig.metadata["magnitude"] == 4.2
    assert sig.isSimulated is False

def test_simulated_fixtures_contain_all_seven_categories():
    fixtures = get_simulated_fixtures()
    categories_found = {f.category for f in fixtures}
    assert SignalCategory.AIRCRAFT in categories_found
    assert SignalCategory.VESSEL in categories_found
    assert SignalCategory.SATELLITE in categories_found
    assert SignalCategory.EARTHQUAKE in categories_found
    assert SignalCategory.WEATHER in categories_found
    assert SignalCategory.CAMERA in categories_found
    assert SignalCategory.INFRASTRUCTURE in categories_found

    # Verify every fixture is explicitly labeled as simulated
    for f in fixtures:
        assert f.isSimulated is True
        assert f.dataStatus == DataStatus.SIMULATED
        assert f.sourceUrl is not None
        assert f.rawRecordHash is not None

def test_weather_forecast_distinguished_from_observation():
    fixtures = get_simulated_fixtures()
    wx_alerts = [f for f in fixtures if f.category == SignalCategory.WEATHER]
    assert len(wx_alerts) > 0
    alert = wx_alerts[0]
    assert alert.validFrom is not None
    assert alert.validUntil is not None
    # Valid until must be after valid from
    assert alert.validUntil > alert.validFrom

def test_invalid_geojson_coordinate_range():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        SignalEnvelope(
            id="bad-coord",
            sourceId="test",
            category=SignalCategory.AIRCRAFT,
            signalType="state-vector",
            geometry=GeoJSONGeometry(type=GeometryType.POINT, coordinates=[250.0, 30.0]),
            latitude=30.0,
            longitude=250.0,
            observedAt=now,
            ingestedAt=now
        )

