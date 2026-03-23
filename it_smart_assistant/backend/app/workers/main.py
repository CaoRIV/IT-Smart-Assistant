"""Infrastructure worker scaffold for background jobs.

This process is intentionally lightweight for now. It prepares the runtime
environment, verifies Redis connectivity, and stays alive as a dedicated worker
container so future ingest/OCR/export jobs can be moved out of the API process
without changing the Docker topology again.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from app.clients.redis import RedisClient
from app.core.config import settings
from app.knowledge import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR
from app.knowledge.admin_store import ensure_admin_dirs
from app.services.chat_attachment import ensure_chat_attachment_dir

logger = logging.getLogger("app.worker")


async def healthcheck() -> bool:
    """Simple connectivity check used by the worker bootstrap."""
    redis = RedisClient()
    await redis.connect()
    try:
        return await redis.ping()
    finally:
        await redis.close()


async def run_worker() -> None:
    """Run the worker heartbeat loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    ensure_admin_dirs()
    DEFAULT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_chat_attachment_dir()

    redis = RedisClient()
    await redis.connect()

    stop_event = asyncio.Event()

    def _request_shutdown() -> None:
        logger.info("Shutdown signal received. Stopping worker...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            asyncio.get_running_loop().add_signal_handler(sig, _request_shutdown)

    logger.info(
        "Worker started | storage_backend=%s | redis=%s | bucket=%s | heartbeat=%ss",
        settings.STORAGE_BACKEND,
        settings.REDIS_URL,
        settings.S3_BUCKET,
        settings.WORKER_HEARTBEAT_SECONDS,
    )

    try:
        while not stop_event.is_set():
            if await redis.ping():
                logger.info("Worker heartbeat OK")
            else:
                logger.warning("Worker heartbeat failed: Redis is unavailable")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.WORKER_HEARTBEAT_SECONDS)
            except TimeoutError:
                continue
    finally:
        await redis.close()
        logger.info("Worker stopped")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
