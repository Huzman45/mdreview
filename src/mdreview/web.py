"""Browser-facing routes."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import render, store
from .api import get_conn, get_settings
from .config import Settings
from .models import ReviewStatus
from .store import NotFound, StoreError

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
    request: Request,
    conn: sqlite3.Connection,
    document: store.Document,
    n: int,
    *,
    error: str | None = None,
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
            "error": error,
            **_sidebar_context(conn, document, version),
        },
    )


def _sidebar_context(
    conn: sqlite3.Connection, document: store.Document, version: store.Version
) -> dict[str, object]:
    """Everything the comment sidebar needs.

    Editing is only offered on the latest version and only while it is still
    pending; commenting on a closed round would produce feedback no agent will
    ever be told about.
    """
    latest = store.latest_version(conn, document.id)
    is_latest = latest is not None and latest.n == version.n
    return {
        "slug": document.slug,
        "version": version,
        "comments": store.list_comments(conn, version.id),
        "unresolved": store.count_unresolved(conn, version.id),
        "can_edit": is_latest and version.status is ReviewStatus.PENDING,
        "is_latest": is_latest,
    }


def _sidebar(
    request: Request,
    conn: sqlite3.Connection,
    document: store.Document,
    version: store.Version,
    *,
    error: str | None = None,
    decision_error: str | None = None,
) -> HTMLResponse:
    context = _sidebar_context(conn, document, version)
    context["error"] = error
    context["decision_error"] = decision_error
    return templates.TemplateResponse(request, "_sidebar.html", context)


@router.post("/d/{slug}/v/{n}/decision", response_class=HTMLResponse)
def record_decision(
    slug: str,
    n: int,
    request: Request,
    conn: Conn,
    status_value: Annotated[str, Form(alias="status")] = "",
    note: Annotated[str, Form()] = "",
) -> HTMLResponse:
    document = _require_document(conn, slug)
    version = _require_version(conn, document, n)

    try:
        decision = ReviewStatus(status_value)
    except ValueError:
        return _sidebar(request, conn, document, version, decision_error="Unknown decision.")

    try:
        store.decide(conn, version=version, status=decision, note=note)
    except store.Conflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except StoreError as exc:
        return _sidebar(request, conn, document, version, decision_error=str(exc))

    refreshed = store.require_version(conn, document.id, n)
    return _sidebar(request, conn, document, refreshed)


@router.post("/d/{slug}/v/{n}/comments", response_class=HTMLResponse)
def create_comment(
    slug: str,
    n: int,
    request: Request,
    conn: Conn,
    line_start: Annotated[str, Form()] = "",
    line_end: Annotated[str, Form()] = "",
    body: Annotated[str, Form()] = "",
) -> HTMLResponse:
    document = _require_document(conn, slug)
    version = _require_version(conn, document, n)

    try:
        start, end = int(line_start), int(line_end)
    except ValueError:
        return _sidebar(request, conn, document, version, error="Select a block first.")

    try:
        store.create_comment(conn, version=version, line_start=start, line_end=end, body=body)
    except StoreError as exc:
        return _sidebar(request, conn, document, version, error=str(exc))

    return _sidebar(request, conn, document, version)


@router.post("/d/{slug}/v/{n}/comments/{ref}/resolve", response_class=HTMLResponse)
def resolve_comment(slug: str, n: int, ref: str, request: Request, conn: Conn) -> HTMLResponse:
    document = _require_document(conn, slug)
    version = _require_version(conn, document, n)
    try:
        store.resolve_comment(conn, version.id, ref)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _sidebar(request, conn, document, version)


def _require_version(
    conn: sqlite3.Connection, document: store.Document, n: int
) -> store.Version:
    try:
        return store.require_version(conn, document.id, n)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _require_document(conn: sqlite3.Connection, slug: str) -> store.Document:
    try:
        return store.require_document(conn, slug)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
