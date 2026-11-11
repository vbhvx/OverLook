# backend/tests/conftest.py
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.container import build_container
from backend.app.main import create_app
from backend.app.providers.base import BaseProviderAdapter
from backend.app.schemas.signals import (
    DataStatus,
    GeoJSONGeometry,
    GeometryType,
    SignalCategory,
    SignalEnvelope,
)

POSTGIS_URL = os.getenv("OVERLOOK_TEST_DATABASE_URL")


def make_signal(
    sid: str,
    lon: float = -122.4,
    lat: float = 37.8,
    observed: Optional[datetime] = None,
    category: SignalCategory = SignalCategory.EARTHQUAKE,
    source_id: str = "usgs-earthquakes",
    record_hash: str = "h1",
    status: DataStatus = DataStatus.ACTUAL,
    simulated: bool = False,
    **metadata: Any,
) -> SignalEnvelope:
    observed = observed or datetime.now(timezone.utc)
    return SignalEnvelope(
        id=sid,
        sourceId=source_id,
        sourceRecordId=sid,
        category=category,
        signalType="test",
        geometry=GeoJSONGeometry(type=GeometryType.POINT, coordinates=[lon, lat]),
        latitude=lat,
        longitude=lon,
        observedAt=observed,
        ingestedAt=observed,
        dataStatus=status,
        isSimulated=simulated,
        rawRecordHash=record_hash,
        metadata=metadata,
    )


class FakeAdapter(BaseProviderAdapter):
    """Scriptable adapter: returns `signals`, or behaves like a failing provider."""

    source_id = "fake"
    category = "earthquake"
    name = "Fake"

    def __init__(self, signals: Optional[List[SignalEnvelope]] = None) -> None:
        super().__init__()
        self.signals = signals or []
        self.fail_with: Optional[str] = None  # adapter-reported failure status
        self.raise_exc: Optional[Exception] = None
        self.delay: float = 0.0
        self.calls = 0

    async def fetch_signals(self, bbox=None):
        import asyncio

        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.raise_exc:
            raise self.raise_exc
        if self.fail_with:
            self.last_status = self.fail_with
            self.last_error = f"simulated {self.fail_with}"
            return []
        self.last_status = "active"
        self.last_error = None
        return list(self.signals)

    async def check_health(self) -> Dict[str, Any]:
        return {"status": self.last_status}


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        ENVIRONMENT="test",
        DATABASE_URL="memory://",
        ENABLE_BACKGROUND_SYNC=False,
        RATE_LIMIT_ENABLED=False,
        MANUAL_SYNC_COOLDOWN_SECONDS=0,
        CIRCUIT_FAILURE_THRESHOLD=2,
    )


@pytest.fixture
def client(test_settings):
    from backend.app.api.v1 import sources

    sources._last_manual_sync.clear()
    app = create_app(test_settings, build_container(test_settings))
    with TestClient(app) as c:
        yield c
