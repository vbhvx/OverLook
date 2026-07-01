# backend/tests/test_time_handling.py
from datetime import datetime, timezone, timedelta
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry, GeometryType
)

def test_distinct_temporal_semantics():
    t_obs = datetime(2026, 11, 10, 10, 0, 0, tzinfo=timezone.utc)
    t_pub = datetime(2026, 11, 10, 10, 2, 30, tzinfo=timezone.utc)
    t_ing = datetime(2026, 11, 10, 10, 5, 0, tzinfo=timezone.utc)
    t_from = datetime(2026, 11, 10, 10, 0, 0, tzinfo=timezone.utc)
    t_until = datetime(2026, 11, 10, 14, 0, 0, tzinfo=timezone.utc)

    sig = SignalEnvelope(
        id="time-test-1",
        sourceId="open-meteo",
        category=SignalCategory.WEATHER,
        signalType="weather-forecast",
        geometry=GeoJSONGeometry(type=GeometryType.POINT, coordinates=[0.0, 50.0]),
        latitude=50.0,
        longitude=0.0,
        observedAt=t_obs,
        publishedAt=t_pub,
        ingestedAt=t_ing,
        validFrom=t_from,
        validUntil=t_until,
        dataStatus=DataStatus.FORECAST
    )

    # Ingestion time must not overwrite observation time
    assert sig.observedAt != sig.ingestedAt
    assert sig.publishedAt > sig.observedAt
    assert sig.ingestedAt > sig.publishedAt
    assert sig.validUntil > sig.validFrom

def test_epoch_conversion_handling():
    # USGS time is in ms epoch: e.g. 1700000000000
    epoch_ms = 1794308113640
    dt_utc = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    assert dt_utc.tzinfo == timezone.utc
    assert dt_utc.year >= 2026

