"""JSON API consumed by the CLI."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from . import db, store
from .config import Settings
from .models import ReviewStatus
from .store import NotFound, StoreError

router = APIRouter(prefix="/api")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.settings.database)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
Config = Annotated[Settings, Depends(get_settings)]


def review_url(settings: Settings, slug: str) -> str:
    return f"{settings.base_url}/d/{slug}"


# -- schemas ----------------------------------------------------------------


class SubmitRequest(BaseModel):
    content: str = Field(description="Full markdown source of the document.")
    slug: str | None = None
    title: str | None = None
    project_path: str | None = None
    session_id: str | None = None
    source_name: str = "document"


class VersionSummary(BaseModel):
    n: int
    status: ReviewStatus
    content_sha: str
    decision_note: str | None
    decided_at: str | None
    created_at: str


class SubmitResponse(BaseModel):
    slug: str
    title: str
    version: int
    status: ReviewStatus
    url: str
    reused: bool


class DocumentResponse(BaseModel):
    slug: str
    title: str
    project_path: str | None
    session_id: str | None
    created_at: str
    url: str
    latest: VersionSummary
    versions: list[int]


class DocumentListItem(BaseModel):
    slug: str
    title: str
    project_path: str | None
    version: int
    status: ReviewStatus
    url: str
    created_at: str


# -- routes -----------------------------------------------------------------


@router.post("/documents", response_model=SubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_document(payload: SubmitRequest, conn: Conn, settings: Config) -> SubmitResponse:
    try:
        result = store.submit(
            conn,
            content=payload.content,
            slug=payload.slug,
            title=payload.title,
            project_path=payload.project_path,
            session_id=payload.session_id,
            source_name=payload.source_name,
        )
    except StoreError as exc:
        raise HTTPException(422, str(exc)) from exc

    return SubmitResponse(
        slug=result.document.slug,
        title=result.document.title,
        version=result.version.n,
        status=result.version.status,
        url=review_url(settings, result.document.slug),
        reused=result.reused,
    )


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents(
    conn: Conn, settings: Config, pending: bool = False
) -> list[DocumentListItem]:
    return [
        DocumentListItem(
            slug=item.document.slug,
            title=item.document.title,
            project_path=item.document.project_path,
            version=item.version.n,
            status=item.version.status,
            url=review_url(settings, item.document.slug),
            created_at=item.version.created_at,
        )
        for item in store.list_documents(conn, pending_only=pending)
    ]


@router.get("/documents/{slug}", response_model=DocumentResponse)
def get_document(slug: str, conn: Conn, settings: Config) -> DocumentResponse:
    document = _require(conn, slug)
    latest = store.latest_version(conn, document.id)
    if latest is None:  # pragma: no cover - a document always has a version
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document has no versions")
    return DocumentResponse(
        slug=document.slug,
        title=document.title,
        project_path=document.project_path,
        session_id=document.session_id,
        created_at=document.created_at,
        url=review_url(settings, document.slug),
        latest=VersionSummary(
            n=latest.n,
            status=latest.status,
            content_sha=latest.content_sha,
            decision_note=latest.decision_note,
            decided_at=latest.decided_at,
            created_at=latest.created_at,
        ),
        versions=[version.n for version in store.list_versions(conn, document.id)],
    )


def _require(conn: sqlite3.Connection, slug: str) -> store.Document:
    try:
        return store.require_document(conn, slug)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
