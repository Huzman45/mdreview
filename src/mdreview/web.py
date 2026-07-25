"""Browser-facing routes."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import render, store
from .api import get_conn, get_settings
from .config import Settings
from .store import NotFound

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

router = APIRouter()

Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
Config = Annotated[Settings, Depends(get_settings)]


@router.get("/", response_class=HTMLResponse)
def index(request: Request, conn: Conn) -> HTMLResponse:
    summaries = store.list_documents(conn)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"summaries": summaries},
    )


@router.get("/d/{slug}", response_class=HTMLResponse)
def document_latest(slug: str, request: Request, conn: Conn) -> HTMLResponse:
    document = _require_document(conn, slug)
    latest = store.latest_version(conn, document.id)
    if latest is None:  # pragma: no cover - documents always have a version
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document has no versions")
    return _document_page(request, conn, document, latest.n)


@router.get("/d/{slug}/v/{n}", response_class=HTMLResponse)
def document_version(slug: str, n: int, request: Request, conn: Conn) -> HTMLResponse:
    document = _require_document(conn, slug)
    return _document_page(request, conn, document, n)


def _document_page(
    request: Request, conn: sqlite3.Connection, document: store.Document, n: int
) -> HTMLResponse:
    try:
        version = store.require_version(conn, document.id, n)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    versions = [v.n for v in store.list_versions(conn, document.id)]
    rendered = render.render(version.content)

    return templates.TemplateResponse(
        request,
        "document.html",
        {
            "document": document,
            "version": version,
            "versions": versions,
            "is_latest": n == max(versions),
            "body": rendered.html,
            "blocks": rendered.blocks,
        },
    )


def _require_document(conn: sqlite3.Connection, slug: str) -> store.Document:
    try:
        return store.require_document(conn, slug)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
