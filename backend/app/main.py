# backend/app/main.py
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.app.api.errors import install_error_handlers
from backend.app.api.v1 import api_v1_router
from backend.app.config import Settings
from backend.app.config import settings as default_settings
from backend.app.container import Container, build_container
from backend.app.core.logging import configure_logging
from backend.app.core.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    TokenBucketLimiter,
)

logger = logging.getLogger("overlook")


def create_app(settings: Optional[Settings] = None, container: Optional[Container] = None) -> FastAPI:
    settings = settings or default_settings
    configure_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
    container = container or build_container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "starting api",
            extra={
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "store": "postgis" if settings.uses_postgis else "memory",
                "embeddedScheduler": settings.ENABLE_BACKGROUND_SYNC,
            },
        )
        await container.start(run_scheduler=settings.ENABLE_BACKGROUND_SYNC)
        try:
            yield
        finally:
            logger.info("shutting down api")
            await container.stop()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Public Signal Intelligence & Situational Awareness Platform API. "
            "Consolidates public, authorized signals across Aircraft, Vessels, Satellites, "
            "Earthquakes, Weather, Public Cameras, and Infrastructure."
        ),
        lifespan=lifespan,
    )
    app.state.container = container
    app.state.settings = settings

    # Added innermost-first; RequestContext ends up outermost so even rate-limited
    # and CORS-rejected responses carry a request ID and are measured.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            limiter=TokenBucketLimiter(settings.RATE_LIMIT_PER_MINUTE / 60.0, settings.RATE_LIMIT_BURST),
            trusted_proxies=settings.TRUSTED_PROXY_COUNT,
        )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.ENVIRONMENT == "production")
    app.add_middleware(RequestContextMiddleware)

    install_error_handlers(app)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docsUrl": "/docs",
            "apiPrefix": settings.API_V1_PREFIX,
        }

    return app


app = create_app()
