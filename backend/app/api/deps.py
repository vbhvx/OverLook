# backend/app/api/deps.py
from fastapi import Request

from backend.app.config import Settings
from backend.app.container import Container
from backend.app.core.events import EventBus
from backend.app.correlation.engine import CorrelationEngine
from backend.app.ingestion.service import IngestionService
from backend.app.storage.base import SignalStore


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_settings(request: Request) -> Settings:
    return get_container(request).settings


def get_store(request: Request) -> SignalStore:
    return get_container(request).store


def get_ingestion(request: Request) -> IngestionService:
    return get_container(request).ingestion


def get_correlation(request: Request) -> CorrelationEngine:
    return get_container(request).correlation


def get_bus(request: Request) -> EventBus:
    return get_container(request).bus
