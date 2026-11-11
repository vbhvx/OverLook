# backend/app/ingestion/leader.py
"""
Leader election, so that N replicas running the scheduler ingest exactly once.

Uses a session-level Postgres advisory lock held on a dedicated connection. If
the leader dies, Postgres drops its session and the lock, and a standby picks
it up on its next attempt — no lease timers, no external coordinator.
"""
import contextlib
import logging
from typing import Optional

from backend.app.core.events import asyncpg_dsn

logger = logging.getLogger("overlook.leader")

# Arbitrary but fixed 64-bit key identifying "the OverLook ingestion leader".
ADVISORY_LOCK_KEY = 0x0E7E_100C


class LeaderElector:
    """Single-process deployments are always the leader."""

    async def ensure(self) -> bool:
        return True

    async def release(self) -> None:
        pass


class PostgresAdvisoryLeader(LeaderElector):
    def __init__(self, database_url: str) -> None:
        self._dsn = asyncpg_dsn(database_url)
        self._conn = None
        self._is_leader = False

    async def ensure(self) -> bool:
        import asyncpg

        if self._is_leader and self._conn is not None:
            try:
                await self._conn.execute("SELECT 1")
                return True
            except Exception:
                logger.warning("lost leader connection; leadership released")
                await self._drop()

        try:
            if self._conn is None or self._conn.is_closed():
                self._conn = await asyncpg.connect(self._dsn)
            acquired: Optional[bool] = await self._conn.fetchval(
                "SELECT pg_try_advisory_lock($1)", ADVISORY_LOCK_KEY
            )
        except Exception:
            logger.warning("leader election unavailable", exc_info=True)
            await self._drop()
            return False

        if acquired and not self._is_leader:
            logger.info("acquired ingestion leadership")
        self._is_leader = bool(acquired)
        return self._is_leader

    async def release(self) -> None:
        if self._conn is not None and self._is_leader:
            with contextlib.suppress(Exception):
                await self._conn.execute("SELECT pg_advisory_unlock($1)", ADVISORY_LOCK_KEY)
        await self._drop()

    async def _drop(self) -> None:
        self._is_leader = False
        if self._conn is not None:
            with contextlib.suppress(Exception):
                await self._conn.close()
        self._conn = None
