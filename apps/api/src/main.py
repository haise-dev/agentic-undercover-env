from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import settings
from src.core.logging import configure_logging, log_startup_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level="DEBUG" if settings.APP_ENV == "development" else "INFO")
    log_startup_status(settings)
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
