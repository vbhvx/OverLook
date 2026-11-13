# backend/migrations/env.py
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import settings

# Migrations are hand-written SQL (PostGIS types, functional indexes), so there
# is no ORM metadata to autogenerate from.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=settings.DATABASE_URL, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    if not settings.uses_postgis:
        raise SystemExit("DATABASE_URL must be a postgresql+asyncpg:// URL to run migrations")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
