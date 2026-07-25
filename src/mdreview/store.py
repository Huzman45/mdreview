"""All SQL lives here.

Keeping every query in one module means the schema can be reasoned about in a
single file, and lets the domain be tested without going through HTTP.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from .db import transaction
from .models import Document, ReviewStatus, Version

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_HEADING = re.compile(r"^\s{0,3}#\s+(.+?)\s*$", re.MULTILINE)


class StoreError(RuntimeError):
    """A domain rule was violated."""


class NotFound(StoreError):
    """The requested entity does not exist."""


def now() -> str:
    """ISO-8601 UTC. SQLite has no date type and this text form sorts correctly."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    slug = _SLUG_STRIP.sub("-", value.strip().lower()).strip("-")
    return slug or "document"


def derive_title(content: str, fallback: str) -> str:
    """Prefer the document's own first heading over a filename."""
    match = _HEADING.search(content)
    if match:
        return match.group(1).strip()
    return fallback


# -- documents --------------------------------------------------------------


def unique_slug(conn: sqlite3.Connection, base: str) -> str:
    """Return ``base``, or ``base-2``, ``base-3``… if it is already taken.

    Two agents in different projects can easily derive the same slug from the
    same conventional filename, and silently merging their documents would be
    the wrong answer.
    """
    base = slugify(base)
    taken = {
        row["slug"]
        for row in conn.execute(
            "SELECT slug FROM documents WHERE slug = ? OR slug LIKE ?",
            (base, f"{base}-%"),
        )
    }
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def get_document(conn: sqlite3.Connection, slug: str) -> Document | None:
    row = conn.execute("SELECT * FROM documents WHERE slug = ?", (slug,)).fetchone()
    return Document.from_row(row) if row else None


def require_document(conn: sqlite3.Connection, slug: str) -> Document:
    document = get_document(conn, slug)
    if document is None:
        raise NotFound(f"no document with slug {slug!r}")
    return document


def create_document(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    project_path: str | None,
    session_id: str | None,
) -> Document:
    cursor = conn.execute(
        "INSERT INTO documents (slug, title, project_path, session_id, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (slug, title, project_path, session_id, now()),
    )
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return Document.from_row(row)


# -- versions ---------------------------------------------------------------


def latest_version(conn: sqlite3.Connection, document_id: int) -> Version | None:
    row = conn.execute(
        "SELECT * FROM versions WHERE document_id = ? ORDER BY n DESC LIMIT 1",
        (document_id,),
    ).fetchone()
    return Version.from_row(row) if row else None


def get_version(conn: sqlite3.Connection, document_id: int, n: int) -> Version | None:
    row = conn.execute(
        "SELECT * FROM versions WHERE document_id = ? AND n = ?", (document_id, n)
    ).fetchone()
    return Version.from_row(row) if row else None


def require_version(conn: sqlite3.Connection, document_id: int, n: int) -> Version:
    version = get_version(conn, document_id, n)
    if version is None:
        raise NotFound(f"no version {n} for that document")
    return version


def list_versions(conn: sqlite3.Connection, document_id: int) -> list[Version]:
    rows = conn.execute(
        "SELECT * FROM versions WHERE document_id = ? ORDER BY n", (document_id,)
    )
    return [Version.from_row(row) for row in rows]


@dataclass(frozen=True, slots=True)
class Submission:
    document: Document
    version: Version
    reused: bool
    """True when identical content was resubmitted against a pending version."""


def submit(
    conn: sqlite3.Connection,
    *,
    content: str,
    slug: str | None = None,
    title: str | None = None,
    project_path: str | None = None,
    session_id: str | None = None,
    source_name: str = "document",
) -> Submission:
    """Record ``content`` as a new version, opening a review round.

    Resubmitting byte-identical content while the latest version is still
    pending returns that version instead of superseding it. Agents retry, and
    without this a retried submit would silently discard whatever comments the
    reviewer had already written against the version it replaced.

    Once a version has been decided the same content does create a new version:
    the reviewer needs a fresh round to decide again, and the digest match is
    coincidental rather than a retry.
    """
    if not content.strip():
        raise StoreError("refusing to submit an empty document")

    sha = digest(content)
    resolved_title = title or derive_title(content, source_name)

    with transaction(conn):
        document = get_document(conn, slug) if slug else None
        if document is None:
            document = create_document(
                conn,
                slug=slug or unique_slug(conn, source_name),
                title=resolved_title,
                project_path=project_path,
                session_id=session_id,
            )
        else:
            conn.execute(
                "UPDATE documents SET title = ?, project_path = ?, session_id = ? WHERE id = ?",
                (resolved_title, project_path, session_id, document.id),
            )
            document = require_document(conn, document.slug)

        current = latest_version(conn, document.id)
        if (
            current is not None
            and current.content_sha == sha
            and current.status is ReviewStatus.PENDING
        ):
            return Submission(document=document, version=current, reused=True)

        n = (current.n + 1) if current else 1
        cursor = conn.execute(
            "INSERT INTO versions (document_id, n, content, content_sha, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (document.id, n, content, sha, ReviewStatus.PENDING.value, now()),
        )
        row = conn.execute(
            "SELECT * FROM versions WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return Submission(document=document, version=Version.from_row(row), reused=False)


# -- listing ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document: Document
    version: Version


def list_documents(
    conn: sqlite3.Connection, *, pending_only: bool = False
) -> list[DocumentSummary]:
    """Every document with its latest version, newest first."""
    rows = conn.execute(
        """
        SELECT d.*, v.id AS v_id, v.document_id AS v_document_id, v.n AS v_n,
               v.content AS v_content, v.content_sha AS v_content_sha,
               v.status AS v_status, v.decision_note AS v_decision_note,
               v.decided_at AS v_decided_at, v.created_at AS v_created_at
        FROM documents d
        JOIN versions v ON v.document_id = d.id
        WHERE v.n = (SELECT MAX(n) FROM versions WHERE document_id = d.id)
        ORDER BY v.created_at DESC, d.id DESC
        """
    ).fetchall()

    summaries = []
    for row in rows:
        version = Version(
            id=row["v_id"],
            document_id=row["v_document_id"],
            n=row["v_n"],
            content=row["v_content"],
            content_sha=row["v_content_sha"],
            status=ReviewStatus(row["v_status"]),
            decision_note=row["v_decision_note"],
            decided_at=row["v_decided_at"],
            created_at=row["v_created_at"],
        )
        if pending_only and version.status is not ReviewStatus.PENDING:
            continue
        summaries.append(DocumentSummary(document=Document.from_row(row), version=version))
    return summaries
