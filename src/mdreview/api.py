"""JSON API consumed by the CLI."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from . import db, store
from .config import Settings
from .models import CommentState, ReviewStatus
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


# -- comments ---------------------------------------------------------------


class CommentRequest(BaseModel):
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    body: str


class CommentResponse(BaseModel):
    ref: str
    line_start: int
    line_end: int
    quoted: str
    body: str
    state: CommentState
    edited_at: str | None
    created_at: str

    @classmethod
    def of(cls, comment: store.Comment) -> CommentResponse:
        return cls(
            ref=comment.ref,
            line_start=comment.line_start,
            line_end=comment.line_end,
            quoted=comment.quoted,
            body=comment.body,
            state=comment.state,
            edited_at=comment.edited_at,
            created_at=comment.created_at,
        )


def _version(conn: sqlite3.Connection, slug: str, n: int) -> store.Version:
    document = _require(conn, slug)
    try:
        return store.require_version(conn, document.id, n)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post(
    "/documents/{slug}/versions/{n}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(slug: str, n: int, payload: CommentRequest, conn: Conn) -> CommentResponse:
    version = _version(conn, slug, n)
    try:
        comment = store.create_comment(
            conn,
            version=version,
            line_start=payload.line_start,
            line_end=payload.line_end,
            body=payload.body,
        )
    except StoreError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CommentResponse.of(comment)


@router.get("/documents/{slug}/versions/{n}/comments", response_model=list[CommentResponse])
def get_comments(
    slug: str, n: int, conn: Conn, state: CommentState | None = None
) -> list[CommentResponse]:
    version = _version(conn, slug, n)
    states = (state,) if state else None
    return [
        CommentResponse.of(comment)
        for comment in store.list_comments(conn, version.id, states=states)
    ]


# -- decisions --------------------------------------------------------------


class DecisionRequest(BaseModel):
    status: ReviewStatus
    note: str | None = None


class StateResponse(BaseModel):
    slug: str
    title: str
    project_path: str | None
    version: int
    status: ReviewStatus
    decision_note: str | None
    decided_at: str | None
    url: str
    open_comments: list[CommentResponse]


@router.post("/documents/{slug}/versions/{n}/decision", response_model=VersionSummary)
def decide(slug: str, n: int, payload: DecisionRequest, conn: Conn) -> VersionSummary:
    version = _version(conn, slug, n)
    try:
        updated = store.decide(conn, version=version, status=payload.status, note=payload.note)
    except store.Conflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except StoreError as exc:
        raise HTTPException(422, str(exc)) from exc

    return VersionSummary(
        n=updated.n,
        status=updated.status,
        content_sha=updated.content_sha,
        decision_note=updated.decision_note,
        decided_at=updated.decided_at,
        created_at=updated.created_at,
    )


@router.get("/documents/{slug}/state", response_model=StateResponse)
def get_state(slug: str, conn: Conn, settings: Config) -> StateResponse:
    try:
        state = store.document_state(conn, slug)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return StateResponse(
        slug=state.document.slug,
        title=state.document.title,
        project_path=state.document.project_path,
        version=state.version.n,
        status=state.status,
        decision_note=state.version.decision_note,
        decided_at=state.version.decided_at,
        url=review_url(settings, state.document.slug),
        open_comments=[CommentResponse.of(c) for c in state.open_comments],
    )
