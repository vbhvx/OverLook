# backend/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.app.config import settings
from backend.app.api.v1 import api_v1_router
from backend.app.ingestion.synchronizer import synchronizer
from backend.app.models.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("overlook")

background_sync_task = None

async def periodic_sync_worker():
    """Background task periodically synchronizing registered live intelligence sources."""
    while True:
        try:
            logger.info("Executing periodic provider sync cycle...")
            await synchronizer.sync_all_sources()
        except Exception as e:
            logger.error(f"Error in periodic sync cycle: {e}")
        await asyncio.sleep(settings.DEFAULT_SYNC_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting OverLook Platform backend...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database init warning (using in-memory/sqlite fallback): {e}")

    # Load initial deterministic fixtures
    synchronizer.load_initial_fixtures()
    logger.info("Loaded deterministic fixtures across all 7 categories.")

    # Trigger initial ingestion
    try:
        await synchronizer.sync_all_sources()
        logger.info(f"Initial sync complete. {len(synchronizer._signals)} signals active.")
    except Exception as e:
        logger.warning(f"Initial provider sync warning: {e}")

    # Start periodic background worker if enabled
    global background_sync_task
    if settings.ENABLE_BACKGROUND_SYNC:
        background_sync_task = asyncio.create_task(periodic_sync_worker())

    yield

    # Shutdown
    logger.info("Shutting down OverLook Platform backend...")
    if background_sync_task:
        background_sync_task.cancel()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Public Signal Intelligence & Situational Awareness Platform API. "
        "Consolidates public, authorized signals across Aircraft, Vessels, Satellites, "
        "Earthquakes, Weather, Public Cameras, and Infrastructure."
    ),
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "body": str(exc.body) if hasattr(exc, "body") else None
        }
    )

@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docsUrl": "/docs",
        "apiPrefix": settings.API_V1_PREFIX
    }

