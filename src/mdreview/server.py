"""Application factory and the uvicorn entrypoint."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.routing import Match, Router
from starlette.types import ASGIApp, Receive, Scope, Send

from . import __version__, config, db
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

    if not config.is_loopback(settings.host):
        _install_lan_guard(app)
    if settings.root_path:
        app.add_middleware(AcceptMountPrefix, prefix=settings.root_path, router=app.router)

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


class AcceptMountPrefix:
    """Answer on the prefixed paths a page emits, as well as on the bare ones.

    A stripping proxy delivers bare paths, but the URLs the CLI prints name the
    bind address, and opening one of those reaches the server with nothing in
    between. The page then asks for `/mdreview/static/app.css` directly, so
    without this the markup renders with no styling and no JavaScript.

    A bare route always wins, so a prefix that shares a route's leading segment
    — `/api`, say — cannot swallow the route the CLI talks to.
    """

    def __init__(self, app: ASGIApp, prefix: str, router: Router) -> None:
        self.app = app
        self.prefix = prefix
        self.router = router

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            scope = self._strip(scope)
        await self.app(scope, receive, send)

    def _strip(self, scope: Scope) -> Scope:
        root = scope.get("root_path", "")
        path = scope["path"][len(root) :]
        if path != self.prefix and not path.startswith(f"{self.prefix}/"):
            return scope
        if any(route.matches(scope)[0] is not Match.NONE for route in self.router.routes):
            return scope
        bare = path[len(self.prefix) :] or "/"
        stripped = dict(scope, path=root + bare)
        raw = scope.get("raw_path")
        encoded = f"{root}{self.prefix}".encode()
        if raw is not None and raw.startswith(encoded):
            stripped["raw_path"] = root.encode() + (raw[len(encoded) :] or b"/")
        return stripped


def _install_lan_guard(app: FastAPI) -> None:
    """Require a capability token from anything that is not loopback.

    The check is per request rather than per route, so a route added later is
    protected by default. The alternative — a list of protected paths — fails
    silently and totally the first time someone forgets to add one.
    """
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import PlainTextResponse

    from . import tokens

    # Create the token now if it does not exist, so it is on disk before the
    # first request arrives. Comparison re-reads it, which is what lets a
    # rotation take effect without a restart.
    tokens.ensure()

    @app.middleware("http")
    async def guard(request: StarletteRequest, call_next):  # type: ignore[no-untyped-def]
        # Deliberately the connection's peer, never X-Forwarded-For or similar.
        # There is no proxy in front of this service, so such a header is
        # attacker-controlled and honouring it would let a LAN client claim to
        # be loopback and bypass the check entirely.
        peer = request.client.host if request.client else ""
        if config.is_loopback(peer):
            return await call_next(request)

        supplied = request.query_params.get(tokens.QUERY_PARAM) or request.cookies.get(
            tokens.COOKIE_NAME
        )
        if not tokens.matches(supplied):
            # A fixed body: distinguishing a bad token from a missing document
            # would let an unauthenticated caller enumerate the store.
            return PlainTextResponse(
                "Not authorised. Reopen the link printed when the server started.",
                status_code=403,
            )

        response = await call_next(request)
        if request.query_params.get(tokens.QUERY_PARAM):
            # Remember it, so navigating and posting comments do not need the
            # token in every URL. Not Secure: the service is plaintext HTTP by
            # design and that flag would stop the cookie being stored at all.
            response.set_cookie(
                tokens.COOKIE_NAME,
                supplied or "",
                httponly=True,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
            )
        return response


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
    config.require_safe_bind(settings.host, allow_lan=settings.allow_lan)
    uvicorn_config = uvicorn.Config(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
        workers=1,
    )
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
    uvicorn.Server(uvicorn_config).run()
