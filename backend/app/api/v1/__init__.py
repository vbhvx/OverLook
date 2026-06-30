# backend/app/api/v1/__init__.py
from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.sources import router as sources_router
from backend.app.api.v1.layers import router as layers_router
from backend.app.api.v1.signals import router as signals_router
from backend.app.api.v1.timeline import router as timeline_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.regions import router as regions_router
from backend.app.api.v1.map import router as map_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(layers_router)
api_v1_router.include_router(signals_router)
api_v1_router.include_router(timeline_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(regions_router)
api_v1_router.include_router(map_router)

