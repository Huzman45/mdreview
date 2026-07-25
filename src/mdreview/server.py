"""Application factory and the uvicorn entrypoint."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from . import __version__, db
from .config import Settings


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        with db.session(settings.database) as conn:
            version = db.migrate(conn)
        app.state.settings = settings
        app.state.schema_version = version
        yield

    app = FastAPI(
        title="mdreview",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings

    from fastapi.staticfiles import StaticFiles

    from .api import router as api_router
    from .web import STATIC_DIR
    from .web import router as web_router

    app.include_router(api_router)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "schema_version": getattr(app.state, "schema_version", None),
            "pid": os.getpid(),
        }

    return app


def get_settings(app: FastAPI) -> Settings:
    return app.state.settings


def connection_for(settings: Settings) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency yielding a per-request connection."""
    conn = db.connect(settings.database)
    try:
        yield conn
    finally:
        conn.close()


def run(settings: Settings, *, log_file: Path | None = None) -> None:
    """Run the server in the foreground until interrupted."""
    config = uvicorn.Config(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
        workers=1,
    )
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
    uvicorn.Server(config).run()
