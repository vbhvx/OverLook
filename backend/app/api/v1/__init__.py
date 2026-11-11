# backend/app/api/v1/__init__.py
from fastapi import APIRouter

from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.layers import router as layers_router
from backend.app.api.v1.map import router as map_router
from backend.app.api.v1.regions import router as regions_router
from backend.app.api.v1.signals import router as signals_router
from backend.app.api.v1.sources import router as sources_router
from backend.app.api.v1.stream import router as stream_router
from backend.app.api.v1.timeline import router as timeline_router

api_v1_router = APIRouter()
for _router in (
    health_router, sources_router, layers_router, signals_router, timeline_router,
    events_router, regions_router, map_router, stream_router,
):
    api_v1_router.include_router(_router)
