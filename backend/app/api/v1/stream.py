# backend/app/api/v1/stream.py
"""
Server-Sent Events: pushes "data changed" hints to browsers so they refresh
when the worker ingests, instead of polling on a timer.
"""
import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.api.deps import get_bus, get_settings
from backend.app.config import Settings
from backend.app.core.events import EventBus
from backend.app.core.metrics import SSE_CLIENTS

router = APIRouter(prefix="/stream", tags=["Stream"])

KEEPALIVE_SECONDS = 15.0


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def event_stream(request: Request, bus: EventBus) -> AsyncIterator[str]:
    async with bus.subscribe() as queue:
        SSE_CLIENTS.inc()
        try:
            # `retry` tells EventSource how long to wait before reconnecting.
            yield "retry: 5000\n" + format_sse("ready", {})
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    # Comment line: keeps proxies from closing an idle connection.
                    yield ": keepalive\n\n"
                    continue
                yield format_sse(event.get("type", "message"), event)
        finally:
            SSE_CLIENTS.dec()


@router.get("")
async def stream_events(
    request: Request,
    bus: EventBus = Depends(get_bus),
    settings: Settings = Depends(get_settings),
):
    if bus.subscriber_count >= settings.MAX_SSE_CLIENTS:
        raise HTTPException(status_code=503, detail="Too many stream subscribers", headers={"Retry-After": "30"})
    return StreamingResponse(
        event_stream(request, bus),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
