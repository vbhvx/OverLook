# backend/app/storage/memory.py
"""
In-process signal store.

Every method runs without awaiting, so each call is atomic with respect to the
event loop — no lock is needed. Queries are linear scans, which is fine for the
few thousand records of a dev session; anything larger belongs in PostGIS.
"""
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional, Sequence, Tuple

from backend.app.geospatial.validation import haversine_distance_km, is_point_in_bbox
from backend.app.schemas.signals import SignalEnvelope
from backend.app.schemas.sources import SourceSyncResult
from backend.app.storage.base import (
    COUNTABLE_FIELDS,
    NearbySignal,
    SignalQuery,
    SignalStore,
    SourceState,
    UpsertStats,
)

MAX_SYNC_RUNS_PER_SOURCE = 200


def _matches(sig: SignalEnvelope, q: SignalQuery) -> bool:
    if q.category and sig.category.value != q.category:
        return False
    if q.source_id and sig.sourceId != q.source_id:
        return False
    if q.data_status and sig.dataStatus.value != q.data_status:
        return False
    if q.start and sig.observedAt < q.start:
        return False
    if q.end and sig.observedAt > q.end:
        return False
    if q.bbox and not is_point_in_bbox(sig.longitude, sig.latitude, list(q.bbox)):
        return False
    return True


def _field_value(sig: SignalEnvelope, field_name: str) -> str:
    if field_name == "category":
        return sig.category.value
    if field_name == "data_status":
        return sig.dataStatus.value
    return sig.sourceId


class InMemorySignalStore(SignalStore):
    def __init__(self) -> None:
        self._signals: Dict[str, SignalEnvelope] = {}
        # Bounded per source, so run history can't grow without limit.
        self._runs: Dict[str, Deque[SourceSyncResult]] = {}
        self._states: Dict[str, SourceState] = {}

    async def ping(self) -> bool:
        return True

    async def upsert_signals(self, signals: Sequence[SignalEnvelope], seen_at: datetime) -> UpsertStats:
        stats = UpsertStats()
        for sig in signals:
            existing = self._signals.get(sig.id)
            if existing is None:
                self._signals[sig.id] = sig.model_copy(update={"lastSeenAt": seen_at})
                stats.inserted += 1
            elif existing.rawRecordHash != sig.rawRecordHash:
                self._signals[sig.id] = sig.model_copy(
                    update={"ingestedAt": existing.ingestedAt, "lastSeenAt": seen_at}
                )
                stats.updated += 1
            else:
                self._signals[sig.id] = existing.model_copy(update={"lastSeenAt": seen_at})
                stats.unchanged += 1
        return stats

    async def get_signal(self, signal_id: str) -> Optional[SignalEnvelope]:
        return self._signals.get(signal_id)

    async def query_signals(self, query: SignalQuery) -> Tuple[List[SignalEnvelope], int]:
        matched = [s for s in self._signals.values() if _matches(s, query)]
        # Two stable sorts: id ascending, then observedAt descending.
        matched.sort(key=lambda s: s.id)
        matched.sort(key=lambda s: s.observedAt, reverse=True)
        return matched[query.offset: query.offset + query.limit], len(matched)

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
        found: List[NearbySignal] = []
        for sig in self._signals.values():
            if sig.id == exclude_id or not (start <= sig.observedAt <= end):
                continue
            dist = haversine_distance_km(lat, lon, sig.latitude, sig.longitude)
            if dist <= radius_km:
                found.append(NearbySignal(sig, dist))
        found.sort(key=lambda n: (n.distance_km, n.signal.id))
        return found[:limit]

    async def timeline(
        self,
        start: datetime,
        end: datetime,
        bucket: timedelta,
        category: Optional[str] = None,
    ) -> Dict[datetime, Dict[str, int]]:
        out: Dict[datetime, Dict[str, int]] = {}
        width = bucket.total_seconds()
        for sig in self._signals.values():
            if category and sig.category.value != category:
                continue
            if not (start <= sig.observedAt <= end):
                continue
            idx = int((sig.observedAt - start).total_seconds() // width)
            key = start + idx * bucket
            counts = out.setdefault(key, {})
            counts[sig.category.value] = counts.get(sig.category.value, 0) + 1
        return out

    async def count_by(self, field_name: str) -> Dict[str, int]:
        if field_name not in COUNTABLE_FIELDS:
            raise ValueError(f"Cannot group by {field_name!r}")
        counts: Dict[str, int] = {}
        for sig in self._signals.values():
            key = _field_value(sig, field_name)
            counts[key] = counts.get(key, 0) + 1
        return counts

    async def prune(self, last_seen_before: datetime) -> int:
        doomed = [
            sid for sid, s in self._signals.items()
            if not s.isSimulated and (s.lastSeenAt or s.ingestedAt) < last_seen_before
        ]
        for sid in doomed:
            del self._signals[sid]
        return len(doomed)

    async def record_sync_run(self, result: SourceSyncResult) -> None:
        runs = self._runs.setdefault(result.sourceId, deque(maxlen=MAX_SYNC_RUNS_PER_SOURCE))
        runs.append(result)

    async def list_sync_runs(self, source_id: str, limit: int) -> List[SourceSyncResult]:
        runs = list(self._runs.get(source_id, ()))
        return list(reversed(runs))[:limit]

    async def save_source_state(self, source_id: str, state: SourceState) -> None:
        self._states[source_id] = state

    async def load_source_states(self) -> Dict[str, SourceState]:
        return dict(self._states)
