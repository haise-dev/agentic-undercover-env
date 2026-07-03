from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.config import settings
from src.core.logging import configure_logging, get_logger, log_startup_status
from src.core.redis import get_redis_client

logger = get_logger("aue.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level="DEBUG" if settings.APP_ENV == "development" else "INFO")
    log_startup_status(settings)

    # Redis startup check (non-fatal)
    try:
        async with get_redis_client() as redis:
            ok = await redis.ping()
            if ok:
                logger.info("Redis connection: OK (%s)", settings.REDIS_URL)
            else:
                logger.warning("Redis ping returned False — check Redis health")
    except RedisConnectionError as exc:
        logger.critical(
            "FATAL: Cannot connect to Redis at %s — %s. "
            "Pub/Sub features will be unavailable.",
            settings.REDIS_URL,
            exc,
        )

    yield


app = FastAPI(
    title="AUE — Agentic Undercover Environment",
    description="Multi-agent social deduction game simulation API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "aue-api",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }
