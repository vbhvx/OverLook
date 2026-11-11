# backend/tests/test_scheduler.py
import asyncio

import pytest

from backend.app.core.events import EventBus
from backend.app.ingestion.leader import LeaderElector
from backend.app.ingestion.scheduler import RETRY_BASE_SECONDS, IngestionScheduler
from backend.app.ingestion.service import IngestionService
from backend.app.storage.memory import InMemorySignalStore
from backend.tests.conftest import FakeAdapter, make_signal

SRC = "usgs-earthquakes"
SLOW_SRC = "open-meteo"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class NeverLeader(LeaderElector):
    async def ensure(self) -> bool:
        return False


@pytest.fixture
def adapters():
    return {SRC: FakeAdapter([make_signal("a")]), SLOW_SRC: FakeAdapter([make_signal("b")])}


@pytest.fixture
def scheduler(test_settings, adapters):
    service = IngestionService(InMemorySignalStore(), EventBus(), test_settings, adapters=adapters)
    return IngestionScheduler(service, LeaderElector(), max_backoff_seconds=600, clock=Clock())


async def test_tick_runs_due_sources_and_schedules_by_interval(scheduler, adapters):
    await scheduler.tick()
    assert adapters[SRC].calls == 1 and adapters[SLOW_SRC].calls == 1
    clock = scheduler._clock
    assert scheduler.next_run[SRC] == clock.now + scheduler.interval_for(SRC)

    # Not due yet: nothing runs.
    await scheduler.tick()
    assert adapters[SRC].calls == 1

    # Only the faster source becomes due first.
    clock.now += scheduler.interval_for(SRC)
    await scheduler.tick()
    assert adapters[SRC].calls == 2 and adapters[SLOW_SRC].calls == 1


async def test_failure_backs_off_exponentially_but_never_beyond_interval(scheduler, adapters):
    adapters[SRC].fail_with = "degraded"
    delays = []
    for _ in range(2):
        scheduler.next_run[SRC] = scheduler._clock.now
        await scheduler.tick()
        delays.append(scheduler.next_run[SRC] - scheduler._clock.now)
    assert RETRY_BASE_SECONDS / 2 <= delays[0] <= RETRY_BASE_SECONDS
    assert delays[1] <= scheduler.interval_for(SRC)
    assert scheduler.failures[SRC] == 2


async def test_open_circuit_waits_for_breaker_reset(scheduler, adapters):
    adapters[SRC].fail_with = "degraded"
    for _ in range(3):  # 2 failures open the circuit, the 3rd call is skipped
        scheduler.next_run[SRC] = scheduler._clock.now
        await scheduler.tick()
    reset = scheduler.service.breakers[SRC].reset_timeout
    assert scheduler.next_run[SRC] - scheduler._clock.now == pytest.approx(reset)


async def test_success_after_failures_restores_normal_cadence(scheduler, adapters):
    adapters[SRC].fail_with = "degraded"
    await scheduler.tick()
    adapters[SRC].fail_with = None
    scheduler.next_run[SRC] = scheduler._clock.now
    await scheduler.tick()
    assert scheduler.failures[SRC] == 0
    assert scheduler.next_run[SRC] - scheduler._clock.now == scheduler.interval_for(SRC)


async def test_standby_replica_never_ingests(test_settings, adapters):
    service = IngestionService(InMemorySignalStore(), EventBus(), test_settings, adapters=adapters)
    sched = IngestionScheduler(service, NeverLeader(), max_backoff_seconds=600)
    stop = asyncio.Event()
    task = asyncio.create_task(sched.run(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=2)
    assert adapters[SRC].calls == 0


async def test_leader_run_loop_ingests_and_stops_cleanly(test_settings, adapters):
    service = IngestionService(InMemorySignalStore(), EventBus(), test_settings, adapters=adapters)
    sched = IngestionScheduler(service, LeaderElector(), max_backoff_seconds=600)
    stop = asyncio.Event()
    task = asyncio.create_task(sched.run(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=2)
    assert adapters[SRC].calls == 1
    assert await service.store.get_signal("a") is not None
