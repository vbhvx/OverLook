# backend/app/container.py
"""
Composition root. The API and the worker build the same object graph from
settings; tests build it with fakes. Nothing else constructs infrastructure.
"""
import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from backend.app.config import Settings
from backend.app.core.events import EventBus
from backend.app.correlation.engine import CorrelationEngine
from backend.app.ingestion.leader import LeaderElector, PostgresAdvisoryLeader
from backend.app.ingestion.scheduler import IngestionScheduler
from backend.app.ingestion.service import IngestionService
from backend.app.providers.base import BaseProviderAdapter
from backend.app.storage.base import SignalStore
from backend.app.storage.factory import build_event_bus, build_store

logger = logging.getLogger("overlook.container")


@dataclass
class Container:
    settings: Settings
    store: SignalStore
    bus: EventBus
    ingestion: IngestionService
    correlation: CorrelationEngine
    _scheduler_task: Optional[asyncio.Task] = field(default=None, repr=False)
    # Created in start(): on Python <3.10 an Event binds to the loop current at creation.
    _stop: Optional[asyncio.Event] = field(default=None, repr=False)

    async def start(self, run_scheduler: bool) -> None:
        self._stop = asyncio.Event()
        await self.store.init()
        await self.bus.start()
        if self.settings.SEED_FIXTURES:
            # Idempotent upsert, so every replica can safely run it.
            await self.ingestion.seed_fixtures()
        if run_scheduler:
            scheduler = IngestionScheduler(self.ingestion, self.leader(), self.settings.MAX_BACKOFF_SECONDS)
            self._scheduler_task = asyncio.create_task(scheduler.run(self._stop), name="ingestion-scheduler")

    def leader(self) -> LeaderElector:
        if self.settings.uses_postgis:
            return PostgresAdvisoryLeader(self.settings.DATABASE_URL)
        return LeaderElector()

    async def wait(self) -> None:
        if self._scheduler_task:
            await self._scheduler_task

    async def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
        if self._scheduler_task:
            # Graceful: the scheduler finishes its in-flight tick, then releases leadership.
            with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(self._scheduler_task, timeout=30)
        await self.bus.stop()
        await self.store.close()


def build_container(
    settings: Settings,
    *,
    store: Optional[SignalStore] = None,
    adapters: Optional[Dict[str, BaseProviderAdapter]] = None,
    listen_events: bool = True,
) -> Container:
    store = store or build_store(settings)
    bus = build_event_bus(settings, listen=listen_events)
    return Container(
        settings=settings,
        store=store,
        bus=bus,
        ingestion=IngestionService(store, bus, settings, adapters=adapters),
        correlation=CorrelationEngine(store),
    )
