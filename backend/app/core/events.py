# backend/app/core/events.py
"""
Domain event fan-out.

The ingestion worker publishes events (e.g. "a source finished syncing"); every
API replica relays them to its connected browsers over SSE. In single-process
mode the bus is an in-memory fan-out. With PostGIS it rides on Postgres
LISTEN/NOTIFY, so no extra broker is needed to connect worker and API.
"""
import asyncio
import contextlib
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional, Set

logger = logging.getLogger("overlook.events")

CHANNEL = "overlook_events"
SUBSCRIBER_QUEUE_SIZE = 100


class EventBus:
    """In-process fan-out. Subclasses change how events arrive, not how they fan out."""

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def publish(self, event: Dict[str, Any]) -> None:
        self._deliver(event)

    def _deliver(self, event: Dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                # Slow consumer: drop its oldest event rather than block everyone
                # or grow memory without bound. Events are refresh hints, so a
                # dropped one only means the client refreshes on the next event.
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            queue.put_nowait(event)

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncIterator["asyncio.Queue[Dict[str, Any]]"]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


def asyncpg_dsn(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+asyncpg://", "postgresql://", 1)


class PostgresEventBus(EventBus):
    """Fan-out across processes using Postgres LISTEN/NOTIFY."""

    RECONNECT_DELAY_SECONDS = 2.0

    def __init__(self, database_url: str, listen: bool = True) -> None:
        super().__init__()
        self._dsn = asyncpg_dsn(database_url)
        self._listen = listen
        self._publish_conn = None
        self._publish_lock: Optional[asyncio.Lock] = None
        self._listener_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._listen:
            self._listener_task = asyncio.create_task(self._listen_forever(), name="event-listener")

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
        if self._publish_conn is not None:
            await self._publish_conn.close()

    async def publish(self, event: Dict[str, Any]) -> None:
        import asyncpg

        payload = json.dumps(event, default=str)
        if self._publish_lock is None:
            self._publish_lock = asyncio.Lock()
        async with self._publish_lock:
            try:
                if self._publish_conn is None or self._publish_conn.is_closed():
                    self._publish_conn = await asyncpg.connect(self._dsn)
                await self._publish_conn.execute("SELECT pg_notify($1, $2)", CHANNEL, payload)
            except Exception:
                # Events are best-effort hints; ingestion must not fail because of them.
                logger.warning("event publish failed", exc_info=True)
                self._publish_conn = None

    async def _listen_forever(self) -> None:
        import asyncpg

        def on_notify(_conn, _pid, _channel, payload: str) -> None:
            try:
                self._deliver(json.loads(payload))
            except ValueError:
                logger.warning("discarding malformed event payload")

        while True:
            conn = None
            try:
                conn = await asyncpg.connect(self._dsn)
                await conn.add_listener(CHANNEL, on_notify)
                logger.info("event listener connected", extra={"channel": CHANNEL})
                # Notifications arrive via the callback; just watch the connection.
                while not conn.is_closed():
                    await asyncio.sleep(5)
                    await conn.execute("SELECT 1")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("event listener disconnected; reconnecting", exc_info=True)
            finally:
                if conn is not None and not conn.is_closed():
                    with contextlib.suppress(Exception):
                        await conn.close()
            await asyncio.sleep(self.RECONNECT_DELAY_SECONDS)
