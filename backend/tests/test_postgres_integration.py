# backend/tests/test_postgres_integration.py
"""
Distributed-coordination behaviour that only exists with Postgres:
LISTEN/NOTIFY fan-out, advisory-lock leader election, and the API end to end.
Skipped unless OVERLOOK_TEST_DATABASE_URL points at a migrated PostGIS database.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app.core.events import PostgresEventBus
from backend.app.ingestion.leader import PostgresAdvisoryLeader
from backend.tests.conftest import POSTGIS_URL

pytestmark = pytest.mark.skipif(not POSTGIS_URL, reason="OVERLOOK_TEST_DATABASE_URL not set")


async def test_notify_reaches_listener_in_another_bus():
    publisher = PostgresEventBus(POSTGIS_URL, listen=False)
    listener = PostgresEventBus(POSTGIS_URL, listen=True)
    await listener.start()
    try:
        async with listener.subscribe() as queue:
            # Wait for LISTEN to be registered before publishing.
            for _ in range(50):
                await publisher.publish({"type": "probe"})
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    break
                except asyncio.TimeoutError:
                    continue
            else:
                pytest.fail("listener never received a notification")
        assert event == {"type": "probe"}
    finally:
        await publisher.stop()
        await listener.stop()


async def test_exactly_one_leader_and_failover_on_release():
    a, b = PostgresAdvisoryLeader(POSTGIS_URL), PostgresAdvisoryLeader(POSTGIS_URL)
    try:
        assert await a.ensure() is True
        assert await b.ensure() is False, "a second replica must stand by"
        assert await a.ensure() is True, "leadership is sticky while the session lives"

        await a.release()
        assert await b.ensure() is True, "standby takes over once the lock is free"
    finally:
        await a.release()
        await b.release()


async def test_leader_crash_releases_lock():
    a, b = PostgresAdvisoryLeader(POSTGIS_URL), PostgresAdvisoryLeader(POSTGIS_URL)
    try:
        assert await a.ensure()
        # Simulate the leader process dying: its session closes without unlocking.
        await a._conn.close()
        assert await b.ensure() is True
    finally:
        await a.release()
        await b.release()


def test_api_end_to_end_on_postgis(test_settings):
    from backend.app.container import build_container
    from backend.app.main import create_app

    settings = test_settings.model_copy(update={"DATABASE_URL": POSTGIS_URL, "SEED_FIXTURES": True})
    with TestClient(create_app(settings, build_container(settings))) as client:
        assert client.get("/api/v1/health/ready").status_code == 200
        health = client.get("/api/v1/health").json()
        assert health["store"] == "postgis" and health["activeSignals"] >= 7

        bay = client.get("/api/v1/signals?bbox=-123.1,37.2,-121.75,38.3").json()
        assert bay["total"] > 0
        detail = client.get("/api/v1/signals/sim-eq-hayward-fault").json()
        assert detail["correlatedSignals"]
        assert client.get("/api/v1/timeline?hours=24").status_code == 200
        assert client.get("/api/v1/events").json()
