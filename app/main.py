import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.config import Settings, get_settings
from app.db import (
    ensure_schema,
    get_connection,
    get_signal_options,
    get_signal_tile,
)
from app.observability import configure_logging as configure_app_logging

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
MVT_MEDIA_TYPE = "application/vnd.mapbox-vector-tile"


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


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/tilejson/signal.json")
async def signal_tilejson(request: Request) -> dict[str, Any]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "tilejson": "3.0.0",
        "name": "Signal Atlas",
        "description": "Provider and RAT signal quality grid cells.",
        "version": "0.1.0",
        "scheme": "xyz",
        "minzoom": 0,
        "maxzoom": 18,
        "bounds": [-180, -85.051129, 180, 85.051129],
        "tiles": [f"{base_url}/tiles/signal/{{z}}/{{x}}/{{y}}.mvt"],
        "vector_layers": [
            {
                "id": "signal_cells",
                "description": "Signal Atlas processed grid cells",
                "fields": {
                    "provider": "String",
                    "rat": "String",
                    "metric_name": "String",
                    "grid_size_m": "Number",
                    "sample_count": "Number",
                    "avg_dbm": "Number",
                    "min_dbm": "Number",
                    "max_dbm": "Number",
                    "quality_bucket": "String",
                },
            }
        ],
        "attribution": "Signal Atlas",
    }


@app.get("/api/signal/options")
async def signal_options() -> dict[str, Any]:
    settings = get_settings()
    with get_connection(settings) as connection:
        ensure_schema(connection)
        return get_signal_options(connection)


@app.get("/tiles/signal/{zoom}/{tile_x}/{tile_y}.mvt")
async def signal_tile(
    zoom: int,
    tile_x: int,
    tile_y: int,
    provider: str | None = None,
    rat: str | None = None,
) -> Response:
    validate_tile_coordinates(zoom=zoom, tile_x=tile_x, tile_y=tile_y)
    settings = get_settings()
    with get_connection(settings) as connection:
        ensure_schema(connection)
        tile = get_signal_tile(
            connection,
            zoom=zoom,
            tile_x=tile_x,
            tile_y=tile_y,
            provider=provider,
            rat=rat,
        )
    return Response(content=tile, media_type=MVT_MEDIA_TYPE)


def validate_tile_coordinates(*, zoom: int, tile_x: int, tile_y: int) -> None:
    if zoom < 0 or zoom > 22:
        raise HTTPException(status_code=404, detail="Tile zoom is out of range")
    max_tile = 2**zoom
    if tile_x < 0 or tile_x >= max_tile or tile_y < 0 or tile_y >= max_tile:
        raise HTTPException(status_code=404, detail="Tile coordinate is out of range")
