# backend/app/storage/postgis.py
"""
PostGIS-backed signal store.

Storage model: each signal is one row holding the canonical SignalEnvelope as
JSONB (`payload`) plus the handful of columns we filter, sort and index on.
Reads rehydrate from `payload`, so adding a metadata field never needs a
migration; adding a *queryable* field does, which is the trade we want.

Spatial indexing:
  * `geom`  geometry(Geometry, 4326) + GiST — bbox intersection, real footprints
  * `point` geography(Point, 4326)   + GiST — metre-accurate radius search
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from backend.app.schemas.signals import SignalEnvelope
from backend.app.schemas.sources import SourceSyncResult
from backend.app.storage.base import (
    COUNTABLE_FIELDS,
    BBox,
    NearbySignal,
    SignalQuery,
    SignalStore,
    SourceState,
    UpsertStats,
)

SYNC_RUN_RETENTION = timedelta(days=7)
UPSERT_CHUNK = 500

_UPSERT_SQL = text("""
    INSERT INTO signals (
        id, source_id, category, data_status, is_simulated,
        observed_at, ingested_at, last_seen_at, raw_record_hash,
        geom, point, payload
    ) VALUES (
        :id, :source_id, :category, :data_status, :is_simulated,
        :observed_at, :ingested_at, :last_seen_at, :raw_record_hash,
        ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
        CAST(:payload AS jsonb)
    )
    ON CONFLICT (id) DO UPDATE SET
        source_id       = EXCLUDED.source_id,
        category        = EXCLUDED.category,
        data_status     = EXCLUDED.data_status,
        is_simulated    = EXCLUDED.is_simulated,
        observed_at     = EXCLUDED.observed_at,
        last_seen_at    = EXCLUDED.last_seen_at,
        raw_record_hash = EXCLUDED.raw_record_hash,
        geom            = EXCLUDED.geom,
        point           = EXCLUDED.point,
        payload         = EXCLUDED.payload
""")


def _bbox_clause(bbox: BBox, params: Dict[str, Any]) -> str:
    west, south, east, north = bbox
    params.update(bs=south, bn=north)
    if west <= east:
        params.update(bw=west, be=east)
        return "ST_Intersects(geom, ST_MakeEnvelope(:bw, :bs, :be, :bn, 4326))"
    # Antimeridian crossing: split into two envelopes, each on one side of ±180.
    params.update(bw=west, be=east)
    return (
        "(ST_Intersects(geom, ST_MakeEnvelope(:bw, :bs, 180, :bn, 4326))"
        " OR ST_Intersects(geom, ST_MakeEnvelope(-180, :bs, :be, :bn, 4326)))"
    )


def _where(q: SignalQuery) -> Tuple[str, Dict[str, Any]]:
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    if q.category:
        clauses.append("category = :category")
        params["category"] = q.category
    if q.source_id:
        clauses.append("source_id = :source_id")
        params["source_id"] = q.source_id
    if q.data_status:
        clauses.append("data_status = :data_status")
        params["data_status"] = q.data_status
    if q.start:
        clauses.append("observed_at >= :start")
        params["start"] = q.start
    if q.end:
        clauses.append("observed_at <= :end")
        params["end"] = q.end
    if q.bbox:
        clauses.append(_bbox_clause(q.bbox, params))
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", params


def _row_params(sig: SignalEnvelope) -> Dict[str, Any]:
    return {
        "id": sig.id,
        "source_id": sig.sourceId,
        "category": sig.category.value,
        "data_status": sig.dataStatus.value,
        "is_simulated": sig.isSimulated,
        "observed_at": sig.observedAt,
        "ingested_at": sig.ingestedAt,
        "last_seen_at": sig.lastSeenAt,
        "raw_record_hash": sig.rawRecordHash,
        # Altitude/depth is dropped by ST_Force2D on insert and kept only in payload.
        "geom": sig.geometry.model_dump_json(),
        "lon": sig.longitude,
        "lat": sig.latitude,
        "payload": sig.model_dump_json(),
    }


def _hydrate(payload: Any) -> SignalEnvelope:
    if isinstance(payload, str):
        payload = json.loads(payload)
    return SignalEnvelope.model_validate(payload)


class PostGISSignalStore(SignalStore):
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 10) -> None:
        self._url = database_url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self.engine: Optional[AsyncEngine] = None

    async def init(self) -> None:
        self.engine = create_async_engine(
            self._url,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            pool_pre_ping=True,
        )

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()

    @property
    def _engine(self) -> AsyncEngine:
        if self.engine is None:
            raise RuntimeError("PostGISSignalStore.init() was not called")
        return self.engine

    async def ping(self) -> bool:
        # Touch the schema, not just the socket: a reachable but unmigrated
        # database must not be reported ready.
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1 FROM signals LIMIT 1"))
            return True
        except Exception:
            return False

    # --- signals -----------------------------------------------------------
    async def upsert_signals(self, signals: Sequence[SignalEnvelope], seen_at: datetime) -> UpsertStats:
        stats = UpsertStats()
        # A provider occasionally repeats an ID within one payload; last one wins.
        unique = list({s.id: s for s in signals}.values())
        async with self._engine.begin() as conn:
            for i in range(0, len(unique), UPSERT_CHUNK):
                chunk = unique[i: i + UPSERT_CHUNK]
                existing = {
                    row.id: (row.raw_record_hash, row.ingested_at)
                    for row in await conn.execute(
                        text(
                            "SELECT id, raw_record_hash, ingested_at FROM signals "
                            "WHERE id = ANY(CAST(:ids AS text[])) FOR UPDATE"
                        ),
                        {"ids": [s.id for s in chunk]},
                    )
                }
                writes: List[Dict[str, Any]] = []
                unchanged_ids: List[str] = []
                for sig in chunk:
                    prior = existing.get(sig.id)
                    if prior is None:
                        stats.inserted += 1
                        writes.append(_row_params(sig.model_copy(update={"lastSeenAt": seen_at})))
                    elif prior[0] != sig.rawRecordHash:
                        stats.updated += 1
                        writes.append(_row_params(
                            sig.model_copy(update={"ingestedAt": prior[1], "lastSeenAt": seen_at})
                        ))
                    else:
                        stats.unchanged += 1
                        unchanged_ids.append(sig.id)
                if writes:
                    await conn.execute(_UPSERT_SQL, writes)
                if unchanged_ids:
                    await conn.execute(
                        text("""
                            UPDATE signals
                               SET last_seen_at = :seen,
                                   payload = jsonb_set(payload, '{lastSeenAt}', to_jsonb(CAST(:seen_iso AS text)))
                             WHERE id = ANY(CAST(:ids AS text[]))
                        """),
                        {"seen": seen_at, "seen_iso": seen_at.isoformat(), "ids": unchanged_ids},
                    )
        return stats

    async def get_signal(self, signal_id: str) -> Optional[SignalEnvelope]:
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                text("SELECT payload FROM signals WHERE id = :id"), {"id": signal_id}
            )).first()
        return _hydrate(row.payload) if row else None

    async def query_signals(self, query: SignalQuery) -> Tuple[List[SignalEnvelope], int]:
        where, params = _where(query)
        async with self._engine.connect() as conn:
            total = (await conn.execute(text(f"SELECT count(*) FROM signals {where}"), params)).scalar_one()
            rows = await conn.execute(
                text(
                    f"SELECT payload FROM signals {where} "
                    "ORDER BY observed_at DESC, id ASC LIMIT :limit OFFSET :offset"
                ),
                {**params, "limit": query.limit, "offset": query.offset},
            )
            items = [_hydrate(r.payload) for r in rows]
        return items, int(total)

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
        async with self._engine.connect() as conn:
            rows = await conn.execute(
                text("""
                    WITH origin AS (
                        SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS g
                    )
                    SELECT s.payload, ST_Distance(s.point, origin.g) / 1000.0 AS distance_km
                      FROM signals s, origin
                     WHERE ST_DWithin(s.point, origin.g, :meters)
                       AND s.observed_at BETWEEN :start AND :end
                       AND (CAST(:exclude AS text) IS NULL OR s.id <> :exclude)
                     ORDER BY distance_km ASC, s.id ASC
                     LIMIT :limit
                """),
                {
                    "lon": lon, "lat": lat, "meters": radius_km * 1000.0,
                    "start": start, "end": end, "exclude": exclude_id, "limit": limit,
                },
            )
            return [NearbySignal(_hydrate(r.payload), float(r.distance_km)) for r in rows]

    async def timeline(
        self,
        start: datetime,
        end: datetime,
        bucket: timedelta,
        category: Optional[str] = None,
    ) -> Dict[datetime, Dict[str, int]]:
        params: Dict[str, Any] = {"bucket": bucket, "start": start, "end": end}
        cat_clause = ""
        if category:
            cat_clause = "AND category = :category"
            params["category"] = category
        async with self._engine.connect() as conn:
            rows = await conn.execute(
                text(f"""
                    SELECT date_bin(:bucket, observed_at, :start) AS bucket, category, count(*) AS n
                      FROM signals
                     WHERE observed_at >= :start AND observed_at <= :end {cat_clause}
                     GROUP BY 1, 2
                """),
                params,
            )
            out: Dict[datetime, Dict[str, int]] = {}
            for r in rows:
                out.setdefault(r.bucket, {})[r.category] = int(r.n)
        return out

    async def count_by(self, field_name: str) -> Dict[str, int]:
        if field_name not in COUNTABLE_FIELDS:
            raise ValueError(f"Cannot group by {field_name!r}")
        # field_name is whitelisted above, so interpolating it is safe.
        async with self._engine.connect() as conn:
            rows = await conn.execute(text(f"SELECT {field_name} AS k, count(*) AS n FROM signals GROUP BY 1"))
            return {r.k: int(r.n) for r in rows}

    async def prune(self, last_seen_before: datetime) -> int:
        async with self._engine.begin() as conn:
            res = await conn.execute(
                text("DELETE FROM signals WHERE NOT is_simulated AND last_seen_at < :cutoff"),
                {"cutoff": last_seen_before},
            )
            await conn.execute(
                text("DELETE FROM sync_runs WHERE started_at < :cutoff"),
                {"cutoff": last_seen_before - SYNC_RUN_RETENTION},
            )
            return res.rowcount or 0

    # --- ingestion bookkeeping --------------------------------------------
    async def record_sync_run(self, result: SourceSyncResult) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO sync_runs (
                        source_id, status, started_at, duration_ms, records_fetched,
                        records_ingested, records_updated, records_rejected, error_message
                    ) VALUES (
                        :source_id, :status, :started_at, :duration_ms, :fetched,
                        :ingested, :updated, :rejected, :error
                    )
                """),
                {
                    "source_id": result.sourceId, "status": result.status,
                    "started_at": result.timestamp, "duration_ms": result.durationMs,
                    "fetched": result.recordsFetched, "ingested": result.recordsIngested,
                    "updated": result.recordsUpdated, "rejected": result.recordsRejected,
                    "error": result.errorMessage,
                },
            )

    async def list_sync_runs(self, source_id: str, limit: int) -> List[SourceSyncResult]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(
                text("""
                    SELECT * FROM sync_runs WHERE source_id = :sid
                     ORDER BY started_at DESC, id DESC LIMIT :limit
                """),
                {"sid": source_id, "limit": limit},
            )
            return [
                SourceSyncResult(
                    sourceId=r.source_id, status=r.status, timestamp=r.started_at,
                    durationMs=r.duration_ms, recordsFetched=r.records_fetched,
                    recordsIngested=r.records_ingested, recordsUpdated=r.records_updated,
                    recordsRejected=r.records_rejected, errorMessage=r.error_message,
                )
                for r in rows
            ]

    async def save_source_state(self, source_id: str, state: SourceState) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO source_state (
                        source_id, status, last_success_at, last_error_at, last_error_message,
                        consecutive_failures, circuit_state, extra, updated_at
                    ) VALUES (
                        :sid, :status, :ok_at, :err_at, :err_msg, :fails, :circuit,
                        CAST(:extra AS jsonb), now()
                    )
                    ON CONFLICT (source_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_success_at = EXCLUDED.last_success_at,
                        last_error_at = EXCLUDED.last_error_at,
                        last_error_message = EXCLUDED.last_error_message,
                        consecutive_failures = EXCLUDED.consecutive_failures,
                        circuit_state = EXCLUDED.circuit_state,
                        extra = EXCLUDED.extra,
                        updated_at = now()
                """),
                {
                    "sid": source_id, "status": state.status,
                    "ok_at": state.last_success_at, "err_at": state.last_error_at,
                    "err_msg": state.last_error_message, "fails": state.consecutive_failures,
                    "circuit": state.circuit_state, "extra": json.dumps(state.extra, default=str),
                },
            )

    async def load_source_states(self) -> Dict[str, SourceState]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(text("SELECT * FROM source_state"))
            return {
                r.source_id: SourceState(
                    status=r.status,
                    last_success_at=r.last_success_at,
                    last_error_at=r.last_error_at,
                    last_error_message=r.last_error_message,
                    consecutive_failures=r.consecutive_failures,
                    circuit_state=r.circuit_state,
                    extra=r.extra or {},
                )
                for r in rows
            }
