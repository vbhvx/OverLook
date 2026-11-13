# backend/app/api/v1/timeline.py
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import get_store
from backend.app.schemas.signals import SignalCategory, TimelineBucket, TimelineResponse
from backend.app.storage.base import SignalStore

router = APIRouter(prefix="/timeline", tags=["Timeline"])


def aligned_window(now: datetime, hours: int, interval_hours: int):
    """
    Bucket edges snap to multiples of the interval (UTC), so two requests a
    minute apart return the same buckets instead of shifting every call.
    """
    width = timedelta(hours=interval_hours)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    end = epoch + ((now - epoch) // width + 1) * width
    return end - timedelta(hours=hours), end, width


@router.get("", response_model=TimelineResponse)
async def get_timeline_histogram(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    interval_hours: int = Query(1, ge=1, le=24, description="Bucket interval size in hours"),
    category: Optional[SignalCategory] = Query(None, description="Optional category filter"),
    store: SignalStore = Depends(get_store),
):
    """Time-bucketed signal counts by category, for timeline navigation."""
    if interval_hours > hours:
        raise HTTPException(status_code=400, detail="interval_hours must not exceed hours")

    start, end, width = aligned_window(datetime.now(timezone.utc), hours, interval_hours)
    counts = await store.timeline(start, end, width, category.value if category else None)

    buckets: List[TimelineBucket] = []
    edge = start
    while edge < end:
        per_cat = counts.get(edge, {})
        buckets.append(TimelineBucket(bucketTime=edge, categoryCounts=per_cat, totalCount=sum(per_cat.values())))
        edge += width

    return TimelineResponse(
        interval=f"{interval_hours}h",
        startTime=start,
        endTime=end,
        buckets=buckets,
        totalSignals=sum(b.totalCount for b in buckets),
    )
