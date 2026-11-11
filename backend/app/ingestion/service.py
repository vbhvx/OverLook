# backend/app/ingestion/service.py
"""
Ingestion pipeline for one provider sync:

    circuit check → fetch (bounded by timeout) → validate → idempotent upsert
    → persist health + run history → metrics → publish event

A provider failure is contained to that provider: it is recorded, counted and
reported, but never raised into the scheduler or the API.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from backend.app.config import Settings
from backend.app.core.events import EventBus
from backend.app.core.metrics import (
    CIRCUIT_STATE,
    INGESTION_DURATION,
    INGESTION_RECORDS,
    INGESTION_RUNS,
    SIGNALS_PRUNED,
)
from backend.app.core.resilience import CIRCUIT_STATE_VALUE, CircuitBreaker, CircuitOpenError
from backend.app.ingestion.fixtures import get_simulated_fixtures
from backend.app.ingestion.registry import SOURCE_DEFINITIONS, SourceDefinition
from backend.app.providers.base import BaseProviderAdapter
from backend.app.schemas.signals import DataStatus, SignalEnvelope
from backend.app.schemas.sources import SourceRegistryItem, SourceSyncResult
from backend.app.storage.base import SignalStore, SourceState

logger = logging.getLogger("overlook.ingestion")

# Adapters report trouble through `last_status` instead of raising.
ADAPTER_FAILURE_STATUSES = {"degraded", "offline", "rate_limited"}
# Clock skew we tolerate before treating an "observation" as future-dated.
MAX_FUTURE_SKEW = timedelta(minutes=10)


class ProviderError(Exception):
    pass


class UnknownSourceError(KeyError):
    pass


def validate_signal(sig: SignalEnvelope, now: datetime) -> Optional[str]:
    """Returns a rejection reason, or None if the record may be ingested."""
    for name in ("observedAt", "ingestedAt"):
        value = getattr(sig, name)
        if value is not None and value.tzinfo is None:
            return f"{name} is timezone-naive"
    # Forecasts describe the future by definition; observations cannot.
    if sig.dataStatus != DataStatus.FORECAST and sig.observedAt > now + MAX_FUTURE_SKEW:
        return "observedAt is in the future"
    if sig.validFrom and sig.validUntil and sig.validUntil < sig.validFrom:
        return "validUntil precedes validFrom"
    return None


class IngestionService:
    def __init__(
        self,
        store: SignalStore,
        bus: EventBus,
        settings: Settings,
        definitions: Optional[Dict[str, SourceDefinition]] = None,
        adapters: Optional[Dict[str, BaseProviderAdapter]] = None,
    ) -> None:
        self.store = store
        self.bus = bus
        self.settings = settings
        self.definitions = definitions or SOURCE_DEFINITIONS
        self.adapters = adapters or {sid: d.adapter_factory() for sid, d in self.definitions.items()}
        self.breakers = {
            sid: CircuitBreaker(settings.CIRCUIT_FAILURE_THRESHOLD, settings.CIRCUIT_RESET_SECONDS)
            for sid in self.adapters
        }
        # One sync per source at a time within this process (scheduler vs manual trigger).
        # Created lazily so they bind to the running loop (matters on Python <3.10).
        self._locks: Dict[str, asyncio.Lock] = {}

    @property
    def source_ids(self) -> List[str]:
        return list(self.adapters)

    async def seed_fixtures(self) -> None:
        stats = await self.store.upsert_signals(get_simulated_fixtures(), datetime.now(timezone.utc))
        logger.info("fixtures seeded", extra={"inserted": stats.inserted, "unchanged": stats.unchanged})

    async def sync_all(self, bbox: Optional[List[float]] = None) -> List[SourceSyncResult]:
        return list(await asyncio.gather(*(self.sync_source(sid, bbox) for sid in self.adapters)))

    async def sync_source(self, source_id: str, bbox: Optional[List[float]] = None) -> SourceSyncResult:
        adapter = self.adapters.get(source_id)
        if adapter is None:
            raise UnknownSourceError(source_id)

        lock = self._locks.setdefault(source_id, asyncio.Lock())
        async with lock:
            return await self._sync_locked(source_id, adapter, bbox)

    async def _sync_locked(
        self, source_id: str, adapter: BaseProviderAdapter, bbox: Optional[List[float]]
    ) -> SourceSyncResult:
        breaker = self.breakers[source_id]
        started = time.perf_counter()
        now = datetime.now(timezone.utc)
        state = (await self.store.load_source_states()).get(source_id) or SourceState()

        try:
            breaker.before_call()
        except CircuitOpenError as exc:
            result = SourceSyncResult(
                sourceId=source_id, status="skipped", recordsFetched=0, recordsIngested=0,
                recordsUpdated=0, recordsRejected=0, durationMs=0,
                errorMessage=str(exc), timestamp=now,
            )
            INGESTION_RUNS.labels(source_id, "skipped").inc()
            return result

        fetched: Sequence[SignalEnvelope] = []
        accepted: List[SignalEnvelope] = []
        rejected = 0
        error: Optional[str] = None
        try:
            # Adapters set their own HTTP timeouts; this bounds the whole fetch,
            # including pagination and parsing, so one provider can't stall a cycle.
            fetched = await asyncio.wait_for(
                adapter.fetch_signals(bbox), timeout=self.settings.PROVIDER_TIMEOUT_SECONDS * 3
            )
            if adapter.last_status in ADAPTER_FAILURE_STATUSES:
                raise ProviderError(adapter.last_error or f"provider reported status '{adapter.last_status}'")
            accepted, rejected = self._validate(source_id, fetched, now)
            stats = await self.store.upsert_signals(accepted, now)
        except asyncio.TimeoutError:
            error = "provider fetch timed out"
        except ProviderError as exc:
            error = str(exc)
        except Exception as exc:  # noqa: BLE001 — isolate every provider failure
            logger.exception("sync crashed", extra={"source": source_id})
            error = f"{type(exc).__name__}: {exc}"

        duration_ms = int((time.perf_counter() - started) * 1000)
        INGESTION_DURATION.labels(source_id).observe(duration_ms / 1000)

        if error is None:
            breaker.record_success()
            state.status = adapter.last_status or "active"
            state.last_success_at = now
            state.consecutive_failures = 0
            result = SourceSyncResult(
                sourceId=source_id, status="success", recordsFetched=len(fetched),
                recordsIngested=stats.inserted, recordsUpdated=stats.updated,
                recordsRejected=rejected, durationMs=duration_ms, timestamp=now,
            )
            for outcome, n in (("inserted", stats.inserted), ("updated", stats.updated),
                               ("unchanged", stats.unchanged), ("rejected", rejected)):
                if n:
                    INGESTION_RECORDS.labels(source_id, outcome).inc(n)
        else:
            breaker.record_failure()
            state.status = "rate_limited" if adapter.last_status == "rate_limited" else "degraded"
            state.last_error_at = now
            state.last_error_message = error
            state.consecutive_failures = breaker.consecutive_failures
            result = SourceSyncResult(
                sourceId=source_id, status="failed", recordsFetched=len(fetched),
                recordsIngested=0, recordsUpdated=0, recordsRejected=rejected,
                durationMs=duration_ms, errorMessage=error, timestamp=now,
            )
            logger.warning("sync failed", extra={"source": source_id, "error": error})

        state.circuit_state = breaker.state.value
        CIRCUIT_STATE.labels(source_id).set(CIRCUIT_STATE_VALUE[breaker.state])
        INGESTION_RUNS.labels(source_id, result.status).inc()

        await self.store.save_source_state(source_id, state)
        await self.store.record_sync_run(result)
        if result.status == "success" and (result.recordsIngested or result.recordsUpdated):
            await self.bus.publish({
                "type": "signals.changed",
                "sourceId": source_id,
                "inserted": result.recordsIngested,
                "updated": result.recordsUpdated,
                "at": now.isoformat(),
            })
        logger.info(
            "sync complete",
            extra={"source": source_id, "status": result.status, "durationMs": duration_ms,
                   "inserted": result.recordsIngested, "updated": result.recordsUpdated},
        )
        return result

    def _validate(
        self, source_id: str, signals: Sequence[SignalEnvelope], now: datetime
    ) -> Tuple[List[SignalEnvelope], int]:
        accepted: List[SignalEnvelope] = []
        rejected = 0
        for sig in signals:
            reason = validate_signal(sig, now)
            if reason:
                rejected += 1
                logger.debug("record rejected", extra={"source": source_id, "id": sig.id, "reason": reason})
            else:
                accepted.append(sig)
        return accepted, rejected

    async def prune(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.settings.SIGNAL_RETENTION_HOURS)
        removed = await self.store.prune(cutoff)
        if removed:
            SIGNALS_PRUNED.inc(removed)
            logger.info("retention prune", extra={"removed": removed})
        return removed

    async def registry(self) -> List[SourceRegistryItem]:
        """Static source metadata merged with live health and record counts."""
        states = await self.store.load_source_states()
        counts = await self.store.count_by("source_id")
        items: List[SourceRegistryItem] = []
        for sid, definition in self.definitions.items():
            item = definition.meta.model_copy()
            st = states.get(sid)
            if st is not None:
                item.status = st.status
                item.lastSuccessAt = st.last_success_at
                item.lastErrorAt = st.last_error_at
                item.lastErrorMessage = st.last_error_message
            item.activeRecordCount = counts.get(sid, 0)
            items.append(item)
        return items
