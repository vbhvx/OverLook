# backend/app/storage/base.py
"""
Storage contract for normalized signals and ingestion bookkeeping.

Two implementations satisfy it:
  * InMemorySignalStore — zero-dependency, for local development and unit tests.
  * PostGISSignalStore  — durable, spatially indexed, shared by API and worker.

Both are exercised by the same contract test suite (tests/test_store_contract.py),
which is what keeps them interchangeable.
"""
import abc
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.app.schemas.signals import SignalEnvelope
from backend.app.schemas.sources import SourceSyncResult

BBox = Tuple[float, float, float, float]  # west, south, east, north

COUNTABLE_FIELDS = ("category", "data_status", "source_id")


@dataclass(frozen=True)
class SignalQuery:
    bbox: Optional[BBox] = None
    category: Optional[str] = None
    source_id: Optional[str] = None
    data_status: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: int = 250
    offset: int = 0


@dataclass
class UpsertStats:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class NearbySignal:
    signal: SignalEnvelope
    distance_km: float


@dataclass
class SourceState:
    """Runtime health of a provider — shared so every API replica reports the worker's view."""
    status: str = "active"
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    consecutive_failures: int = 0
    circuit_state: str = "closed"
    extra: Dict[str, Any] = field(default_factory=dict)


class SignalStore(abc.ABC):
    async def init(self) -> None:  # noqa: B027 — optional hook, default no-op
        """Open connections. Schema is owned by migrations, not by this call."""

    async def close(self) -> None:  # noqa: B027 — optional hook, default no-op
        pass

    @abc.abstractmethod
    async def ping(self) -> bool:
        """Cheap readiness check."""

    # --- signals -----------------------------------------------------------
    @abc.abstractmethod
    async def upsert_signals(self, signals: Sequence[SignalEnvelope], seen_at: datetime) -> UpsertStats:
        """
        Idempotent ingest keyed by signal ID.
          * new ID            → inserted
          * known ID, new hash → payload replaced, original ingestedAt preserved
          * known ID, same hash → only lastSeenAt is bumped
        """

    @abc.abstractmethod
    async def get_signal(self, signal_id: str) -> Optional[SignalEnvelope]:
        ...

    @abc.abstractmethod
    async def query_signals(self, query: SignalQuery) -> Tuple[List[SignalEnvelope], int]:
        """Returns (page ordered by observedAt desc then id, total matching)."""

    @abc.abstractmethod
    async def find_near(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        start: datetime,
        end: datetime,
        exclude_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[NearbySignal]:
        """Signals within radius_km and [start, end], nearest first."""

    @abc.abstractmethod
    async def timeline(
        self,
        start: datetime,
        end: datetime,
        bucket: timedelta,
        category: Optional[str] = None,
    ) -> Dict[datetime, Dict[str, int]]:
        """Counts per (bucket start, category); bucket starts are aligned to `start`."""

    @abc.abstractmethod
    async def count_by(self, field_name: str) -> Dict[str, int]:
        """Counts grouped by one of COUNTABLE_FIELDS."""

    @abc.abstractmethod
    async def prune(self, last_seen_before: datetime) -> int:
        """
        Retention: delete live (non-simulated) signals not seen since the cutoff.
        Simulated fixtures are a fixed, curated set and are never pruned.
        """

    # --- ingestion bookkeeping --------------------------------------------
    @abc.abstractmethod
    async def record_sync_run(self, result: SourceSyncResult) -> None:
        ...

    @abc.abstractmethod
    async def list_sync_runs(self, source_id: str, limit: int) -> List[SourceSyncResult]:
        """Most recent first."""

    @abc.abstractmethod
    async def save_source_state(self, source_id: str, state: SourceState) -> None:
        ...

    @abc.abstractmethod
    async def load_source_states(self) -> Dict[str, SourceState]:
        ...
