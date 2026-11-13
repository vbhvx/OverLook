# backend/tests/test_providers.py
"""
Live-provider parsers against recorded-shape payloads, via httpx.MockTransport.
No network: these pin how we interpret upstream formats and upstream failures.
"""
from datetime import datetime, timezone
from typing import Callable

import httpx
import pytest

from backend.app.providers.open_meteo import OpenMeteoAdapter
from backend.app.providers.opensky_aircraft import OpenSkyAircraftAdapter
from backend.app.providers.usgs_earthquake import USGSEarthquakeAdapter
from backend.app.schemas.signals import DataStatus, SignalCategory

ORIGIN_MS = 1_780_000_000_000  # 2026-05-28T20:26:40Z


def mock(adapter, handler: Callable[[httpx.Request], httpx.Response]):
    adapter.get_http_client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return adapter


def usgs_feature(fid="us7000abcd", lon=-122.25, lat=37.87, depth=8.2, **props):
    base = {
        "mag": 3.8, "magType": "ml", "place": "2 km ESE of Berkeley, CA", "time": ORIGIN_MS,
        "updated": ORIGIN_MS + 600_000, "status": "reviewed", "url": f"https://earthquake.usgs.gov/{fid}",
        "tsunami": 0, "alert": None, "felt": None,
    }
    base.update(props)
    return {"type": "Feature", "id": fid, "properties": base,
            "geometry": {"type": "Point", "coordinates": [lon, lat, depth]}}


async def test_usgs_parses_feature_into_normalized_signal():
    adapter = mock(USGSEarthquakeAdapter(), lambda req: httpx.Response(
        200, json={"type": "FeatureCollection", "features": [usgs_feature()]}
    ))
    [sig] = await adapter.fetch_signals()

    assert sig.id == "eq-us7000abcd" and sig.category == SignalCategory.EARTHQUAKE
    assert (sig.longitude, sig.latitude) == (-122.25, 37.87)
    assert sig.altitudeM == pytest.approx(-8200.0), "depth is stored as negative altitude"
    # Origin time vs. revision time are kept distinct, both in UTC.
    assert sig.observedAt == datetime.fromtimestamp(ORIGIN_MS / 1000, tz=timezone.utc)
    assert sig.publishedAt > sig.observedAt
    assert sig.dataStatus == DataStatus.ACTUAL and sig.isSimulated is False
    assert sig.metadata["magnitude"] == 3.8 and sig.metadata["reviewStatus"] == "reviewed"
    # Missing data stays missing; it is not coerced to zero.
    assert sig.metadata["feltReports"] is None
    assert adapter.last_status == "active"


async def test_usgs_forwards_bbox_as_query_params():
    seen = {}

    def handler(req):
        seen.update(req.url.params)
        return httpx.Response(200, json={"features": []})

    await mock(USGSEarthquakeAdapter(), handler).fetch_signals([-123.0, 37.0, -121.0, 38.5])
    assert seen["minlongitude"] == "-123.0" and seen["maxlatitude"] == "38.5"


async def test_usgs_skips_malformed_features_without_failing_the_batch():
    features = [
        usgs_feature("ok"),
        usgs_feature("no-time", time=None),
        usgs_feature("bad-lat", lat=123.0),
        {"type": "Feature", "id": "no-geom", "properties": {"time": ORIGIN_MS}, "geometry": {}},
    ]
    adapter = mock(USGSEarthquakeAdapter(), lambda req: httpx.Response(200, json={"features": features}))
    signals = await adapter.fetch_signals()
    assert [s.id for s in signals] == ["eq-ok"]


async def test_usgs_revision_changes_record_hash():
    a = await mock(USGSEarthquakeAdapter(), lambda r: httpx.Response(200, json={"features": [usgs_feature()]})).fetch_signals()
    b = await mock(USGSEarthquakeAdapter(), lambda r: httpx.Response(
        200, json={"features": [usgs_feature(mag=4.1)]}
    )).fetch_signals()
    assert a[0].id == b[0].id
    assert a[0].rawRecordHash != b[0].rawRecordHash


@pytest.mark.parametrize("response", [
    httpx.Response(503, text="Service Unavailable"),
])
async def test_usgs_http_error_reports_degraded(response):
    adapter = mock(USGSEarthquakeAdapter(), lambda req: response)
    assert await adapter.fetch_signals() == []
    assert adapter.last_status == "degraded"
    assert "503" in adapter.last_error


async def test_usgs_network_error_reports_degraded():
    def boom(req):
        raise httpx.ConnectError("connection refused", request=req)

    adapter = mock(USGSEarthquakeAdapter(), boom)
    assert await adapter.fetch_signals() == []
    assert adapter.last_status == "degraded"


def opensky_state(icao="a1b2c3", lon=-122.38, lat=37.62, callsign="UAL123 "):
    # icao24, callsign, origin_country, time_position, last_contact, lon, lat, baro_alt,
    # on_ground, velocity, true_track, vertical_rate, sensors, geo_alt, squawk, spi, pos_source
    return [icao, callsign, "United States", 1780000000, 1780000001, lon, lat, 1200.0,
            False, 120.5, 280.0, -3.2, None, 1250.0, "1200", False, 0]


async def test_opensky_parses_state_vectors_and_skips_positionless_aircraft():
    payload = {"time": 1780000005, "states": [opensky_state(), opensky_state("nopos", lon=None, lat=None)]}
    adapter = mock(OpenSkyAircraftAdapter(), lambda req: httpx.Response(200, json=payload))
    signals = await adapter.fetch_signals()
    assert len(signals) == 1
    sig = signals[0]
    assert sig.category == SignalCategory.AIRCRAFT
    assert sig.metadata["callsign"] == "UAL123"
    assert sig.observedAt.tzinfo is not None


async def test_opensky_rate_limit_is_reported_as_failure_status():
    adapter = mock(OpenSkyAircraftAdapter(), lambda req: httpx.Response(429))
    await adapter.fetch_signals()
    # The ingestion service turns this status into a failed run (no stale re-ingest).
    assert adapter.last_status == "rate_limited"


async def test_open_meteo_marks_forecasts_distinct_from_observations():
    payload = {
        "current": {"time": "2026-05-28T20:00", "temperature_2m": 14.2, "relative_humidity_2m": 80,
                    "apparent_temperature": 13.0, "precipitation": 0.0, "weather_code": 3,
                    "wind_speed_10m": 12.0, "wind_direction_10m": 270, "surface_pressure": 1012.0},
        "hourly": {"time": [f"2026-05-28T{h:02d}:00" for h in range(24)],
                   "temperature_2m": [14.0] * 24, "precipitation_probability": [10] * 24,
                   "weather_code": [3] * 24},
    }
    adapter = mock(OpenMeteoAdapter(), lambda req: httpx.Response(200, json=payload))
    signals = await adapter.fetch_signals()
    assert signals
    statuses = {s.dataStatus for s in signals}
    assert DataStatus.FORECAST in statuses
    for s in signals:
        assert s.category == SignalCategory.WEATHER
        if s.dataStatus == DataStatus.FORECAST:
            assert s.metadata.get("isForecast") is True


async def test_open_meteo_total_outage_reports_degraded():
    adapter = mock(OpenMeteoAdapter(), lambda req: httpx.Response(500))
    assert await adapter.fetch_signals() == []
    assert adapter.last_status == "degraded"
