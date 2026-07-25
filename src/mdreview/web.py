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


def display_path(value: str | None) -> str:
    """Abbreviate the home directory so a project path fits the chrome.

    Truncating with an ellipsis instead would hide the tail, which is the only
    informative part of an absolute path.
    """
    if not value:
        return ""
    home = str(Path.home())
    if value == home:
        return "~"
    if value.startswith(home + "/"):
        return "~" + value[len(home) :]
    return value


templates.env.filters["display_path"] = display_path

#: Inlined into <head> so the stored colour scheme is applied before the first
#: paint. Served from a file rather than duplicated in the template, and read
#: once at import because it is our own asset, not user input.
THEME_SCRIPT = (STATIC_DIR / "theme.js").read_text(encoding="utf-8")
templates.env.globals["theme_script"] = THEME_SCRIPT

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
            "previous_version": _previous_version(versions, n),
            "view": "rendered",
            "body": rendered.html,
            "blocks": rendered.blocks,
            "has_diagrams": rendered.has_diagrams,
            "error": error,
            **_sidebar_context(conn, document, version),
        },
    )


def _previous_version(versions: list[int], n: int) -> int | None:
    """The version immediately before ``n``, or None if it is the first."""
    earlier = [v for v in versions if v < n]
    return max(earlier) if earlier else None


@router.get("/d/{slug}/v/{n}/raw", response_class=HTMLResponse)
def document_raw(slug: str, n: int, request: Request, conn: Conn) -> HTMLResponse:
    """The version as numbered source lines.

    This is what makes feedback possible on text no rendered block isolates —
    one line of a fenced block, or one line of a wrapped paragraph. It posts to
    the same comment endpoint with the same line-range anchor, so a comment made
    here is indistinguishable from one made on a rendered block.
    """
    document = _require_document(conn, slug)
    version = _require_version(conn, document, n)
    versions = [v.n for v in store.list_versions(conn, document.id)]

    return templates.TemplateResponse(
        request,
        "raw.html",
        {
            "document": document,
            "version": version,
            "versions": versions,
            "is_latest": n == max(versions),
            "previous_version": _previous_version(versions, n),
            "view": "raw",
            "lines": version.content.splitlines(),
            "has_diagrams": False,
            "error": None,
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
