# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ingestion.synchronizer import synchronizer

@pytest.fixture(scope="module")
def client():
    synchronizer.load_initial_fixtures()
    with TestClient(app) as c:
        yield c

def test_api_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "activeSignals" in data
    assert "sources" in data

def test_list_sources(client):
    resp = client.get("/api/v1/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) >= 7
    source_ids = [s["id"] for s in sources]
    assert "usgs-earthquakes" in source_ids
    assert "open-meteo" in source_ids

def test_list_layers(client):
    resp = client.get("/api/v1/layers")
    assert resp.status_code == 200
    layers = resp.json()
    assert len(layers) >= 7
    cats = [l["category"] for l in layers]
    assert "earthquake" in cats
    assert "aircraft" in cats
    assert "vessel" in cats

def test_query_signals_no_filter(client):
    resp = client.get("/api/v1/signals?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0

def test_query_signals_by_category(client):
    resp = client.get("/api/v1/signals?category=aircraft")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["category"] == "aircraft"

def test_query_signals_by_bbox(client):
    # SF Bay Area
    resp = client.get("/api/v1/signals?bbox=-123.0,37.0,-121.5,38.5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["bboxApplied"] is True

def test_query_signals_invalid_bbox_returns_400(client):
    resp = client.get("/api/v1/signals?bbox=invalid-coordinates")
    assert resp.status_code == 400

def test_timeline_histogram(client):
    resp = client.get("/api/v1/timeline?hours=24&interval_hours=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "buckets" in data
    assert "totalSignals" in data

def test_investigation_events(client):
    resp = client.get("/api/v1/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)

def test_saved_regions(client):
    resp = client.get("/api/v1/regions")
    assert resp.status_code == 200
    regions = resp.json()
    assert len(regions) >= 5
    names = [r["name"] for r in regions]
    assert "San Francisco Bay Area" in names

def test_map_summary(client):
    resp = client.get("/api/v1/map/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "activeSignalsCount" in data
    assert "categoryBreakdown" in data
    assert "statusBreakdown" in data

