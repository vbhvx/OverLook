# backend/app/worker.py
"""
Standalone ingestion worker:  python -m backend.app.worker

Run any number of replicas; a Postgres advisory lock makes exactly one of them
the active ingester while the rest stand by. Exposes Prometheus metrics on
WORKER_METRICS_PORT and shuts down gracefully on SIGTERM/SIGINT.
"""
import asyncio
import logging
import signal

from prometheus_client import start_http_server

from backend.app.config import settings
from backend.app.container import build_container
from backend.app.core.logging import configure_logging

logger = logging.getLogger("overlook.worker")


async def main() -> None:
    configure_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
    if not settings.uses_postgis:
        logger.warning("worker is using the in-memory store; ingested data is not visible to the API")

    start_http_server(settings.WORKER_METRICS_PORT)
    # The worker only publishes events; it has no SSE clients to listen for.
    container = build_container(settings, listen_events=False)

    loop = asyncio.get_running_loop()
    stopping = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)

    await container.start(run_scheduler=True)
    logger.info("worker started", extra={"metricsPort": settings.WORKER_METRICS_PORT})
    await stopping.wait()
    logger.info("worker stopping")
    await container.stop()


if __name__ == "__main__":
    asyncio.run(main())
