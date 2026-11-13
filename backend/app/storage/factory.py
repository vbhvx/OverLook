# backend/app/storage/factory.py
from backend.app.config import Settings
from backend.app.core.events import EventBus, PostgresEventBus
from backend.app.storage.base import SignalStore
from backend.app.storage.memory import InMemorySignalStore


def build_store(settings: Settings) -> SignalStore:
    if settings.uses_postgis:
        from backend.app.storage.postgis import PostGISSignalStore

        return PostGISSignalStore(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )
    return InMemorySignalStore()


def build_event_bus(settings: Settings, listen: bool = True) -> EventBus:
    if settings.uses_postgis:
        return PostgresEventBus(settings.DATABASE_URL, listen=listen)
    return EventBus()
