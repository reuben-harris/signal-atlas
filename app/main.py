import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.observability import configure_logging as configure_app_logging

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    configure_app_logging(debug=settings.debug, log_format=settings.log_format)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(get_settings())
    yield


app = FastAPI(title="Signal Atlas", lifespan=lifespan)


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
