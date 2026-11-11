# backend/tests/test_store_contract.py
"""
One behavioural contract, run against every SignalStore implementation.
PostGIS runs when OVERLOOK_TEST_DATABASE_URL points at a migrated database
(CI provides one); otherwise only the in-memory store is exercised.
"""
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.schemas.signals import DataStatus, SignalCategory
from backend.app.schemas.sources import SourceSyncResult
from backend.app.storage.base import SignalQuery, SourceState
from backend.app.storage.memory import InMemorySignalStore
from backend.tests.conftest import POSTGIS_URL, make_signal

T0 = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

BACKENDS = ["memory"]
if POSTGIS_URL:
    BACKENDS.append("postgis")


@pytest.fixture(params=BACKENDS)
async def store(request):
    if request.param == "memory":
        s = InMemorySignalStore()
        await s.init()
        yield s
        return

    from sqlalchemy import text

    from backend.app.storage.postgis import PostGISSignalStore

    s = PostGISSignalStore(POSTGIS_URL, pool_size=2, max_overflow=0)
    await s.init()
    async with s.engine.begin() as conn:
        await conn.execute(text("TRUNCATE signals, sync_runs, source_state RESTART IDENTITY"))
    yield s
    await s.close()


# --- idempotent ingest ----------------------------------------------------

async def test_upsert_classifies_insert_update_unchanged(store):
    stats = await store.upsert_signals([make_signal("a"), make_signal("b")], T0)
    assert (stats.inserted, stats.updated, stats.unchanged) == (2, 0, 0)

    stats = await store.upsert_signals([make_signal("a"), make_signal("b", record_hash="h2")], T0)
    assert (stats.inserted, stats.updated, stats.unchanged) == (0, 1, 1)

    items, total = await store.query_signals(SignalQuery())
    assert total == 2


async def test_update_preserves_original_ingestion_time(store):
    first = make_signal("a", observed=T0)
    await store.upsert_signals([first], T0)

    later = T0 + timedelta(hours=1)
    revised = make_signal("a", observed=T0, record_hash="h2", magnitude=4.2)
    revised = revised.model_copy(update={"ingestedAt": later})
    await store.upsert_signals([revised], later)

    got = await store.get_signal("a")
    assert got.metadata["magnitude"] == 4.2
    assert got.ingestedAt == first.ingestedAt
    assert got.lastSeenAt == later


async def test_unchanged_record_only_bumps_last_seen(store):
    await store.upsert_signals([make_signal("a", magnitude=1.0)], T0)
    later = T0 + timedelta(minutes=5)
    await store.upsert_signals([make_signal("a", magnitude=1.0)], later)
    got = await store.get_signal("a")
    assert got.lastSeenAt == later
    assert got.metadata["magnitude"] == 1.0


async def test_get_missing_signal_returns_none(store):
    assert await store.get_signal("missing") is None


# --- querying ---------------------------------------------------------------

async def test_query_filters_and_total(store):
    await store.upsert_signals([
        make_signal("eq1", observed=T0),
        make_signal("eq2", observed=T0 - timedelta(hours=2)),
        make_signal("wx1", category=SignalCategory.WEATHER, source_id="open-meteo",
                    status=DataStatus.FORECAST, observed=T0),
    ], T0)

    _, total = await store.query_signals(SignalQuery(category="earthquake"))
    assert total == 2
    items, _ = await store.query_signals(SignalQuery(source_id="open-meteo"))
    assert [s.id for s in items] == ["wx1"]
    items, _ = await store.query_signals(SignalQuery(data_status="forecast"))
    assert [s.id for s in items] == ["wx1"]
    items, _ = await store.query_signals(SignalQuery(start=T0 - timedelta(hours=1)))
    assert {s.id for s in items} == {"eq1", "wx1"}
    items, _ = await store.query_signals(SignalQuery(end=T0 - timedelta(hours=1)))
    assert [s.id for s in items] == ["eq2"]


async def test_query_orders_newest_first_with_stable_tiebreak(store):
    await store.upsert_signals([
        make_signal("c", observed=T0),
        make_signal("a", observed=T0),
        make_signal("b", observed=T0 + timedelta(minutes=1)),
    ], T0)
    items, _ = await store.query_signals(SignalQuery())
    assert [s.id for s in items] == ["b", "a", "c"]


async def test_pagination_returns_full_total(store):
    await store.upsert_signals(
        [make_signal(f"s{i:02d}", observed=T0 - timedelta(minutes=i)) for i in range(25)], T0
    )
    page, total = await store.query_signals(SignalQuery(limit=10, offset=20))
    assert total == 25
    assert [s.id for s in page] == ["s20", "s21", "s22", "s23", "s24"]


async def test_bbox_filter(store):
    await store.upsert_signals([
        make_signal("sf", lon=-122.4, lat=37.8),
        make_signal("tokyo", lon=139.7, lat=35.6),
    ], T0)
    items, _ = await store.query_signals(SignalQuery(bbox=(-123.0, 37.0, -121.0, 38.5)))
    assert [s.id for s in items] == ["sf"]


async def test_bbox_crossing_antimeridian(store):
    await store.upsert_signals([
        make_signal("fiji", lon=178.0, lat=-17.0),
        make_signal("samoa", lon=-172.0, lat=-14.0),
        make_signal("sydney", lon=151.2, lat=-33.9),
    ], T0)
    items, _ = await store.query_signals(SignalQuery(bbox=(170.0, -20.0, -170.0, -10.0)))
    assert {s.id for s in items} == {"fiji", "samoa"}


# --- spatial-temporal neighbourhood --------------------------------------

async def test_find_near_orders_by_distance_and_respects_window(store):
    await store.upsert_signals([
        make_signal("origin", lon=-122.27, lat=37.87, observed=T0),
        make_signal("near", lon=-122.42, lat=37.77, observed=T0),             # ~17 km
        make_signal("mid", lon=-122.0, lat=37.5, observed=T0),               # ~47 km
        make_signal("far", lon=-118.24, lat=34.05, observed=T0),             # ~560 km
        make_signal("old", lon=-122.27, lat=37.88, observed=T0 - timedelta(days=2)),
    ], T0)

    found = await store.find_near(
        37.87, -122.27, radius_km=100, start=T0 - timedelta(hours=6), end=T0 + timedelta(hours=6),
        exclude_id="origin",
    )
    assert [n.signal.id for n in found] == ["near", "mid"]
    # Haversine (memory) and spheroid (PostGIS) agree to well under 1%.
    assert found[0].distance_km == pytest.approx(17.0, rel=0.05)


async def test_find_near_limit(store):
    await store.upsert_signals(
        [make_signal(f"p{i}", lon=-122.4 + i * 0.01, lat=37.8, observed=T0) for i in range(5)], T0
    )
    found = await store.find_near(37.8, -122.4, 50, T0 - timedelta(hours=1), T0 + timedelta(hours=1), limit=2)
    assert [n.signal.id for n in found] == ["p0", "p1"]


# --- aggregation ------------------------------------------------------------

async def test_timeline_buckets_align_to_start(store):
    await store.upsert_signals([
        make_signal("a", observed=T0 + timedelta(minutes=10)),
        make_signal("b", observed=T0 + timedelta(minutes=50)),
        make_signal("c", observed=T0 + timedelta(hours=2, minutes=5),
                    category=SignalCategory.WEATHER, source_id="open-meteo"),
        make_signal("outside", observed=T0 - timedelta(hours=1)),
    ], T0)
    buckets = await store.timeline(T0, T0 + timedelta(hours=3), timedelta(hours=1))
    assert buckets == {
        T0: {"earthquake": 2},
        T0 + timedelta(hours=2): {"weather": 1},
    }

    only_wx = await store.timeline(T0, T0 + timedelta(hours=3), timedelta(hours=1), category="weather")
    assert only_wx == {T0 + timedelta(hours=2): {"weather": 1}}


async def test_count_by(store):
    await store.upsert_signals([
        make_signal("a"), make_signal("b"),
        make_signal("c", category=SignalCategory.WEATHER, source_id="open-meteo"),
    ], T0)
    assert await store.count_by("category") == {"earthquake": 2, "weather": 1}
    assert await store.count_by("source_id") == {"usgs-earthquakes": 2, "open-meteo": 1}
    with pytest.raises(ValueError):
        await store.count_by("payload; DROP TABLE signals")


# --- retention --------------------------------------------------------------

async def test_prune_removes_stale_live_data_but_keeps_simulated(store):
    await store.upsert_signals([
        make_signal("stale-live"),
        make_signal("stale-sim", simulated=True, status=DataStatus.SIMULATED),
    ], T0 - timedelta(days=5))
    await store.upsert_signals([make_signal("fresh")], T0)

    removed = await store.prune(T0 - timedelta(days=1))
    assert removed == 1
    _, total = await store.query_signals(SignalQuery())
    assert total == 2
    assert await store.get_signal("stale-live") is None


# --- bookkeeping ------------------------------------------------------------

async def test_sync_runs_newest_first_and_limited(store):
    for i in range(5):
        await store.record_sync_run(SourceSyncResult(
            sourceId="usgs-earthquakes", status="success", recordsFetched=i, recordsIngested=i,
            recordsUpdated=0, recordsRejected=0, durationMs=10, timestamp=T0 + timedelta(minutes=i),
        ))
    await store.record_sync_run(SourceSyncResult(
        sourceId="open-meteo", status="failed", recordsFetched=0, recordsIngested=0,
        recordsUpdated=0, recordsRejected=0, durationMs=5, errorMessage="boom", timestamp=T0,
    ))
    runs = await store.list_sync_runs("usgs-earthquakes", limit=3)
    assert [r.recordsFetched for r in runs] == [4, 3, 2]
    assert (await store.list_sync_runs("open-meteo", 10))[0].errorMessage == "boom"


async def test_source_state_round_trip(store):
    state = SourceState(
        status="degraded", last_error_at=T0, last_error_message="HTTP 503",
        consecutive_failures=2, circuit_state="open",
    )
    await store.save_source_state("usgs-earthquakes", state)
    await store.save_source_state("usgs-earthquakes", SourceState(
        status="active", last_success_at=T0, circuit_state="closed",
    ))
    states = await store.load_source_states()
    assert states["usgs-earthquakes"].status == "active"
    assert states["usgs-earthquakes"].last_success_at == T0
    assert states["usgs-earthquakes"].consecutive_failures == 0


async def test_ping(store):
    assert await store.ping() is True
