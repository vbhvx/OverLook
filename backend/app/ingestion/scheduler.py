# backend/app/ingestion/scheduler.py
"""
Per-source polling scheduler.

Each source runs on its own cadence (registry `sync_interval_seconds`). A failing
source backs off exponentially with jitter, and once its circuit opens it is
not retried until the breaker's reset window has passed. Healthy sources are
never delayed by unhealthy ones.
"""
import asyncio
import contextlib
import logging
import time
from typing import Callable, Dict

from backend.app.core.resilience import backoff_delay
from backend.app.ingestion.leader import LeaderElector
from backend.app.ingestion.service import IngestionService
from backend.app.schemas.sources import SourceSyncResult

logger = logging.getLogger("overlook.scheduler")

RETRY_BASE_SECONDS = 15.0
STANDBY_POLL_SECONDS = 10.0
PRUNE_INTERVAL_SECONDS = 600.0
MAX_IDLE_SECONDS = 5.0


class IngestionScheduler:
    def __init__(
        self,
        service: IngestionService,
        leader: LeaderElector,
        max_backoff_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.service = service
        self.leader = leader
        self.max_backoff = max_backoff_seconds
        self._clock = clock
        now = clock()
        self.next_run: Dict[str, float] = {sid: now for sid in service.source_ids}
        self.failures: Dict[str, int] = {sid: 0 for sid in service.source_ids}
        self._next_prune = now + PRUNE_INTERVAL_SECONDS

    def interval_for(self, source_id: str) -> float:
        return float(self.service.definitions[source_id].sync_interval_seconds)

    def reschedule(self, result: SourceSyncResult) -> float:
        """Sets and returns the delay before this source's next attempt."""
        sid = result.sourceId
        if result.status == "success":
            self.failures[sid] = 0
            delay = self.interval_for(sid)
        elif result.status == "skipped":
            # Circuit open: wait out the breaker instead of hammering it.
            delay = self.service.breakers[sid].reset_timeout
        else:
            self.failures[sid] += 1
            delay = min(
                backoff_delay(self.failures[sid] - 1, RETRY_BASE_SECONDS, self.max_backoff),
                self.interval_for(sid),
            )
        self.next_run[sid] = self._clock() + delay
        return delay

    async def tick(self) -> None:
        """Runs every source that is due, concurrently."""
        now = self._clock()
        due = [sid for sid, at in self.next_run.items() if at <= now]
        if due:
            results = await asyncio.gather(*(self.service.sync_source(sid) for sid in due))
            for r in results:
                self.reschedule(r)
        if now >= self._next_prune:
            self._next_prune = now + PRUNE_INTERVAL_SECONDS
            await self.service.prune()

    async def run(self, stop: asyncio.Event) -> None:
        logger.info("scheduler started", extra={"sources": len(self.next_run)})
        was_leader = False
        try:
            while not stop.is_set():
                if not await self.leader.ensure():
                    if was_leader:
                        logger.warning("leadership lost; standing by")
                    was_leader = False
                    await self._sleep(stop, STANDBY_POLL_SECONDS)
                    continue
                if not was_leader:
                    # Fresh leader: don't trust the old schedule, sync everything now.
                    now = self._clock()
                    self.next_run = {sid: now for sid in self.next_run}
                    was_leader = True
                try:
                    await self.tick()
                except Exception:
                    # A broken store must not kill the scheduler; retry on the next tick.
                    logger.exception("scheduler tick failed")
                wait = min(self.next_run.values()) - self._clock()
                await self._sleep(stop, min(max(wait, 0.5), MAX_IDLE_SECONDS))
        finally:
            await self.leader.release()
            logger.info("scheduler stopped")

    @staticmethod
    async def _sleep(stop: asyncio.Event, seconds: float) -> None:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=seconds)
