# backend/tests/test_api.py
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1.stream import event_stream
from backend.app.container import build_container
from backend.app.core.events import EventBus
from backend.app.main import create_app
from backend.tests.conftest import FakeAdapter, make_signal

# --- health -----------------------------------------------------------------

def test_api_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["storeReachable"] is True
    assert data["activeSignals"] > 0
    assert "sources" in data


def test_liveness_and_readiness(client):
    assert client.get("/api/v1/health/live").json() == {"status": "alive"}
    assert client.get("/api/v1/health/ready").status_code == 200


def test_readiness_fails_when_store_is_down(client):
    async def down():
        return False

    client.app.state.container.store.ping = down
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 503
    assert client.get("/api/v1/health").json()["status"] == "unhealthy"


# --- registry, layers, regions ---------------------------------------------

def test_list_sources(client):
    resp = client.get("/api/v1/sources")
    assert resp.status_code == 200
    source_ids = [s["id"] for s in resp.json()]
    assert len(source_ids) >= 7
    assert "usgs-earthquakes" in source_ids and "open-meteo" in source_ids


def test_get_unknown_source_404(client):
    assert client.get("/api/v1/sources/nope").status_code == 404


def test_list_layers(client):
    resp = client.get("/api/v1/layers")
    assert resp.status_code == 200
    cats = [layer["category"] for layer in resp.json()]
    assert {"earthquake", "aircraft", "vessel"} <= set(cats)


def test_saved_regions(client):
    names = [r["name"] for r in client.get("/api/v1/regions").json()]
    assert len(names) >= 5
    assert "San Francisco Bay Area" in names


# --- signals ----------------------------------------------------------------

def test_query_signals_no_filter(client):
    data = client.get("/api/v1/signals?limit=50").json()
    assert len(data["items"]) > 0
    assert data["total"] >= len(data["items"])


def test_query_signals_by_category(client):
    data = client.get("/api/v1/signals?category=aircraft").json()
    assert data["items"]
    assert all(item["category"] == "aircraft" for item in data["items"])


def test_query_signals_by_bbox(client):
    data = client.get("/api/v1/signals?bbox=-123.0,37.0,-121.5,38.5").json()
    assert data["meta"]["bboxApplied"] is True
    for item in data["items"]:
        assert -123.0 <= item["longitude"] <= -121.5


@pytest.mark.parametrize("bbox", [
    "invalid-coordinates", "1,2,3", "-200,0,0,10", "0,-95,10,10", "0,10,10,5",
])
def test_query_signals_invalid_bbox_returns_400(client, bbox):
    resp = client.get(f"/api/v1/signals?bbox={bbox}")
    assert resp.status_code == 400
    assert resp.json()["error"] == "bad_request"


def test_unknown_category_is_a_validation_error(client):
    resp = client.get("/api/v1/signals?category=submarine")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "validation_error"
    assert body["details"][0]["loc"] == ["query", "category"]
    assert "input" not in body["details"][0], "request input must not be reflected"


def test_naive_timestamps_are_treated_as_utc(client):
    resp = client.get("/api/v1/signals?start=2020-01-01T00:00:00&end=2099-01-01T00:00:00")
    assert resp.status_code == 200
    assert resp.json()["total"] > 0


def test_start_after_end_rejected(client):
    resp = client.get("/api/v1/signals?start=2026-01-02T00:00:00Z&end=2026-01-01T00:00:00Z")
    assert resp.status_code == 400


def test_limit_is_clamped_to_configured_maximum(client):
    assert client.get("/api/v1/signals?limit=999999").json()["meta"]["limit"] == 1000


def test_signal_detail_includes_provenance_and_neighbours(client):
    resp = client.get("/api/v1/signals/sim-eq-hayward-fault")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provenance"]["isSimulated"] is True
    assert data["correlatedSignals"], "SF Bay fixtures sit within the detail radius"
    for rel in data["correlatedRelations"]:
        assert rel["distanceKm"] <= 60
        assert "does NOT prove causal" in rel["hypothesisDisclaimer"]


def test_signal_detail_404_uses_error_envelope(client):
    resp = client.get("/api/v1/signals/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"
    assert body["requestId"] == resp.headers["x-request-id"]


# --- timeline, events, summary ---------------------------------------------

def test_timeline_histogram(client):
    data = client.get("/api/v1/timeline?hours=24&interval_hours=2").json()
    assert len(data["buckets"]) == 12
    assert data["totalSignals"] == sum(b["totalCount"] for b in data["buckets"])
    # Edges are aligned to the interval, so repeated calls return the same buckets.
    assert data["startTime"].endswith(":00:00Z")
    again = client.get("/api/v1/timeline?hours=24&interval_hours=2").json()
    assert again["startTime"] == data["startTime"]


def test_timeline_rejects_interval_larger_than_window(client):
    assert client.get("/api/v1/timeline?hours=2&interval_hours=6").status_code == 400


def test_investigation_events(client):
    events = client.get("/api/v1/events").json()
    assert events, "fixtures produce at least one seismic or regional event"
    for ev in events:
        assert ev["confidenceLevel"] == "observational_association"
        assert ev["disclaimer"]
    one = client.get(f"/api/v1/events/{events[0]['id']}")
    assert one.status_code == 200 and one.json()["id"] == events[0]["id"]
    assert client.get("/api/v1/events/nope").status_code == 404


def test_map_summary(client):
    data = client.get("/api/v1/map/summary").json()
    assert data["activeSignalsCount"] == sum(data["categoryBreakdown"].values())
    assert "statusBreakdown" in data and "sourceHealth" in data


# --- manual sync ------------------------------------------------------------

@pytest.fixture
def sync_client(test_settings):
    from backend.app.api.v1 import sources

    sources._last_manual_sync.clear()
    adapter = FakeAdapter([make_signal("eq-live-1")])
    settings = test_settings.model_copy(update={"MANUAL_SYNC_COOLDOWN_SECONDS": 60})
    container = build_container(settings, adapters={"usgs-earthquakes": adapter})
    with TestClient(create_app(settings, container)) as c:
        yield c


def test_manual_sync_then_cooldown(sync_client):
    first = sync_client.post("/api/v1/sources/usgs-earthquakes/sync")
    assert first.status_code == 200
    assert first.json()["recordsIngested"] == 1

    second = sync_client.post("/api/v1/sources/usgs-earthquakes/sync")
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0

    runs = sync_client.get("/api/v1/sources/usgs-earthquakes/runs").json()
    assert runs[0]["status"] == "success"
    assert sync_client.get("/api/v1/signals/eq-live-1").status_code == 200


def test_manual_sync_unknown_source(sync_client):
    assert sync_client.post("/api/v1/sources/nope/sync").status_code == 404


# --- cross-cutting HTTP behaviour ------------------------------------------

def test_request_id_is_generated_or_propagated(client):
    assert len(client.get("/api/v1/regions").headers["x-request-id"]) == 32
    resp = client.get("/api/v1/regions", headers={"X-Request-ID": "trace-abc.123"})
    assert resp.headers["x-request-id"] == "trace-abc.123"
    # Unsafe IDs are replaced, not echoed into logs/headers.
    resp = client.get("/api/v1/regions", headers={"X-Request-ID": "bad id\r\nx"})
    assert resp.headers["x-request-id"] != "bad id\r\nx"


def test_security_headers(client):
    headers = client.get("/api/v1/regions").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"


def test_cors_allows_only_configured_origins(client):
    ok = client.get("/api/v1/regions", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    evil = client.get("/api/v1/regions", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


def test_rate_limit_returns_429_with_retry_after(test_settings):
    settings = test_settings.model_copy(update={
        "RATE_LIMIT_ENABLED": True, "RATE_LIMIT_PER_MINUTE": 60, "RATE_LIMIT_BURST": 3,
    })
    with TestClient(create_app(settings, build_container(settings))) as c:
        codes = [c.get("/api/v1/regions").status_code for _ in range(5)]
        assert codes[:3] == [200, 200, 200]
        assert codes[3] == 429
        limited = c.get("/api/v1/regions")
        assert limited.json()["error"] == "rate_limited"
        assert "retry-after" in limited.headers
        # Health probes are never rate limited.
        assert c.get("/api/v1/health/live").status_code == 200


def test_metrics_use_route_templates(client):
    client.get("/api/v1/signals/some-random-id-123")
    body = client.get("/metrics").text
    assert 'route="/api/v1/signals/{signal_id}"' in body
    assert "some-random-id-123" not in body


# --- SSE --------------------------------------------------------------------

class _FakeRequest:
    def __init__(self) -> None:
        self.disconnected = False

    async def is_disconnected(self) -> bool:
        return self.disconnected


async def test_event_stream_relays_bus_events():
    bus, request = EventBus(), _FakeRequest()
    stream = event_stream(request, bus)

    hello = await stream.__anext__()
    assert "event: ready" in hello and hello.startswith("retry: 5000")

    pending = asyncio.ensure_future(stream.__anext__())
    await asyncio.sleep(0)
    await bus.publish({"type": "signals.changed", "sourceId": "usgs-earthquakes"})
    frame = await asyncio.wait_for(pending, timeout=1)
    assert frame.startswith("event: signals.changed\n")
    assert json.loads(frame.split("data: ", 1)[1])["sourceId"] == "usgs-earthquakes"

    request.disconnected = True
    await stream.aclose()
    assert bus.subscriber_count == 0


async def test_slow_subscriber_drops_oldest_instead_of_blocking():
    from backend.app.core.events import SUBSCRIBER_QUEUE_SIZE

    bus = EventBus()
    async with bus.subscribe() as q:
        for i in range(SUBSCRIBER_QUEUE_SIZE + 5):
            await bus.publish({"n": i})
        assert q.qsize() == SUBSCRIBER_QUEUE_SIZE
        assert q.get_nowait()["n"] == 5


def test_unhandled_error_returns_envelope_with_request_id(client):
    async def explode(*_a, **_kw):
        raise RuntimeError("database on fire")

    client.app.state.container.store.count_by = explode
    resp = client.get("/api/v1/layers")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_error"
    assert body["requestId"] == resp.headers["x-request-id"]
    assert "on fire" not in resp.text, "internal details must not leak"


def test_health_reports_unhealthy_instead_of_crashing(client):
    async def explode(*_a, **_kw):
        raise RuntimeError("relation \"signals\" does not exist")

    client.app.state.container.store.count_by = explode
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unhealthy"
