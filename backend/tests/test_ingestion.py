# backend/tests/test_ingestion.py
"""Ingestion pipeline behaviour: isolation, validation, breaker, events, health."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.core.events import EventBus
from backend.app.ingestion.registry import SOURCE_DEFINITIONS
from backend.app.ingestion.service import IngestionService, UnknownSourceError, validate_signal
from backend.app.schemas.signals import DataStatus
from backend.app.storage.base import SignalQuery
from backend.app.storage.memory import InMemorySignalStore
from backend.tests.conftest import FakeAdapter, make_signal

SRC = "usgs-earthquakes"


@pytest.fixture
def adapter():
    return FakeAdapter([make_signal("eq-1"), make_signal("eq-2")])


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def service(test_settings, adapter, bus):
    return IngestionService(InMemorySignalStore(), bus, test_settings, adapters={SRC: adapter})


async def test_successful_sync_ingests_and_records_health(service):
    result = await service.sync_source(SRC)
    assert result.status == "success"
    assert (result.recordsFetched, result.recordsIngested) == (2, 2)

    state = (await service.store.load_source_states())[SRC]
    assert state.status == "active" and state.last_success_at is not None
    assert (await service.store.list_sync_runs(SRC, 5))[0].status == "success"


async def test_resync_of_identical_data_is_idempotent(service):
    await service.sync_source(SRC)
    again = await service.sync_source(SRC)
    assert (again.recordsIngested, again.recordsUpdated) == (0, 0)
    _, total = await service.store.query_signals(SignalQuery())
    assert total == 2


async def test_adapter_reported_failure_is_a_failed_run_and_ingests_nothing(service, adapter):
    adapter.fail_with = "rate_limited"
    result = await service.sync_source(SRC)
    assert result.status == "failed"
    assert "rate_limited" in result.errorMessage

    state = (await service.store.load_source_states())[SRC]
    assert state.status == "rate_limited"
    assert state.consecutive_failures == 1
    _, total = await service.store.query_signals(SignalQuery())
    assert total == 0


async def test_adapter_exception_is_contained(service, adapter):
    adapter.raise_exc = RuntimeError("parser exploded")
    result = await service.sync_source(SRC)
    assert result.status == "failed"
    assert "parser exploded" in result.errorMessage


async def test_slow_provider_times_out(test_settings, bus):
    slow = FakeAdapter([make_signal("x")])
    slow.delay = 0.5
    settings = test_settings.model_copy(update={"PROVIDER_TIMEOUT_SECONDS": 0.05})
    svc = IngestionService(InMemorySignalStore(), bus, settings, adapters={SRC: slow})
    result = await svc.sync_source(SRC)
    assert result.status == "failed"
    assert "timed out" in result.errorMessage


async def test_circuit_opens_after_threshold_and_stops_calling_provider(service, adapter):
    adapter.fail_with = "degraded"
    await service.sync_source(SRC)
    await service.sync_source(SRC)  # threshold is 2 in test settings
    calls = adapter.calls

    skipped = await service.sync_source(SRC)
    assert skipped.status == "skipped"
    assert adapter.calls == calls, "open circuit must not reach the provider"
    assert (await service.store.load_source_states())[SRC].circuit_state == "open"


async def test_one_failing_source_does_not_affect_others(test_settings, bus):
    good, bad = FakeAdapter([make_signal("ok")]), FakeAdapter()
    bad.raise_exc = ConnectionError("down")
    svc = IngestionService(InMemorySignalStore(), bus, test_settings,
                           adapters={SRC: good, "open-meteo": bad})
    results = {r.sourceId: r.status for r in await svc.sync_all()}
    assert results == {SRC: "success", "open-meteo": "failed"}
    assert await svc.store.get_signal("ok") is not None


async def test_future_dated_observations_are_rejected_but_forecasts_are_not(test_settings, bus):
    future = datetime.now(timezone.utc) + timedelta(hours=3)
    adapter = FakeAdapter([
        make_signal("bogus", observed=future),
        make_signal("fcst", observed=future, status=DataStatus.FORECAST),
        make_signal("ok"),
    ])
    svc = IngestionService(InMemorySignalStore(), bus, test_settings, adapters={SRC: adapter})
    result = await svc.sync_source(SRC)
    assert (result.recordsIngested, result.recordsRejected) == (2, 1)
    assert await svc.store.get_signal("bogus") is None


def test_validate_rejects_naive_timestamps():
    sig = make_signal("n").model_copy(update={"observedAt": datetime(2026, 1, 1)})
    assert validate_signal(sig, datetime.now(timezone.utc)) == "observedAt is timezone-naive"


async def test_change_publishes_event_but_no_op_resync_does_not(service, bus):
    async with bus.subscribe() as queue:
        await service.sync_source(SRC)
        event = queue.get_nowait()
        assert event["type"] == "signals.changed"
        assert event["sourceId"] == SRC and event["inserted"] == 2

        await service.sync_source(SRC)
        assert queue.empty()


async def test_concurrent_syncs_of_one_source_are_serialized(service, adapter):
    adapter.delay = 0.05
    results = await asyncio.gather(service.sync_source(SRC), service.sync_source(SRC))
    assert sorted(r.recordsIngested for r in results) == [0, 2]


async def test_unknown_source_raises(service):
    with pytest.raises(UnknownSourceError):
        await service.sync_source("nope")


async def test_registry_merges_static_metadata_with_live_state(service):
    await service.sync_source(SRC)
    registry = {s.id: s for s in await service.registry()}
    assert set(registry) == set(SOURCE_DEFINITIONS)
    assert registry[SRC].activeRecordCount == 2
    assert registry[SRC].lastSuccessAt is not None
    assert registry[SRC].licenseStatus == "public_domain"
