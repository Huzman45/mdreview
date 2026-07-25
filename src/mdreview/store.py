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

from . import render
from .db import transaction
from .models import Comment, CommentState, Document, ReviewStatus, Version

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
        # Feedback on a superseded version is history, not an outstanding
        # request. Anchors are left untouched so the comment stays readable
        # against the text it was written on.
        outdate_open_comments(conn, document.id)
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


# -- comments ---------------------------------------------------------------


def next_ref(conn: sqlite3.Connection, version_id: int) -> str:
    """Allocate the next ``Cn`` reference for a version.

    Numbering restarts per version and counts every comment ever made on it,
    including resolved ones, so a reference is never reused for different
    feedback. The UNIQUE constraint on (version_id, ref) is the backstop.
    """
    count = conn.execute(
        "SELECT COUNT(*) FROM comments WHERE version_id = ?", (version_id,)
    ).fetchone()[0]
    return f"C{count + 1}"


def create_comment(
    conn: sqlite3.Connection,
    *,
    version: Version,
    line_start: int,
    line_end: int,
    body: str,
) -> Comment:
    """Attach a note to a line range of a version.

    The source text is captured now rather than resolved on read, so the
    comment stays meaningful once the version is superseded.
    """
    if not body.strip():
        raise StoreError("refusing to store an empty comment")
    if not render.is_within(version.content, line_start, line_end):
        raise StoreError(
            f"line range {line_start}-{line_end} is outside version "
            f"{version.n}, which has {render.line_count(version.content)} lines"
        )

    quoted = render.quote_lines(version.content, line_start, line_end)
    with transaction(conn):
        ref = next_ref(conn, version.id)
        cursor = conn.execute(
            "INSERT INTO comments"
            " (version_id, ref, line_start, line_end, quoted, body, state, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version.id,
                ref,
                line_start,
                line_end,
                quoted,
                body.strip(),
                CommentState.OPEN.value,
                now(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM comments WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return Comment.from_row(row)


def list_comments(
    conn: sqlite3.Connection,
    version_id: int,
    *,
    states: tuple[CommentState, ...] | None = None,
) -> list[Comment]:
    query = "SELECT * FROM comments WHERE version_id = ?"
    params: list[object] = [version_id]
    if states:
        placeholders = ", ".join("?" for _ in states)
        query += f" AND state IN ({placeholders})"
        params.extend(state.value for state in states)
    query += " ORDER BY id"
    return [Comment.from_row(row) for row in conn.execute(query, params)]


def open_comments(conn: sqlite3.Connection, version_id: int) -> list[Comment]:
    return list_comments(conn, version_id, states=(CommentState.OPEN,))


def get_comment(conn: sqlite3.Connection, version_id: int, ref: str) -> Comment | None:
    row = conn.execute(
        "SELECT * FROM comments WHERE version_id = ? AND ref = ?", (version_id, ref)
    ).fetchone()
    return Comment.from_row(row) if row else None


def resolve_comment(conn: sqlite3.Connection, version_id: int, ref: str) -> Comment:
    """Mark a comment resolved. Idempotent for one already resolved."""
    comment = get_comment(conn, version_id, ref)
    if comment is None:
        raise NotFound(f"no comment {ref!r} on this version")
    if comment.state is CommentState.OPEN:
        conn.execute(
            "UPDATE comments SET state = ? WHERE id = ?",
            (CommentState.RESOLVED.value, comment.id),
        )
        comment = get_comment(conn, version_id, ref)
        assert comment is not None
    return comment


def outdate_open_comments(conn: sqlite3.Connection, document_id: int) -> int:
    """Supersede every open comment on a document. Returns how many changed.

    Comments are marked rather than relocated. Re-anchoring feedback onto
    shifted line numbers is the single largest source of complexity in tools
    like this, and its failure mode — a comment silently attached to the wrong
    passage — is worse than honestly marking it outdated.
    """
    cursor = conn.execute(
        "UPDATE comments SET state = ?"
        " WHERE state = ?"
        "   AND version_id IN (SELECT id FROM versions WHERE document_id = ?)",
        (CommentState.OUTDATED.value, CommentState.OPEN.value, document_id),
    )
    return cursor.rowcount


def count_unresolved(conn: sqlite3.Connection, version_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM comments WHERE version_id = ? AND state = ?",
        (version_id, CommentState.OPEN.value),
    ).fetchone()[0]


# -- decisions --------------------------------------------------------------


class Conflict(StoreError):
    """The version has already been decided."""


DECIDABLE = (
    ReviewStatus.APPROVED,
    ReviewStatus.CHANGES_REQUESTED,
    ReviewStatus.CANCELLED,
)


def decide(
    conn: sqlite3.Connection,
    *,
    version: Version,
    status: ReviewStatus,
    note: str | None = None,
) -> Version:
    """Close a review round.

    A version carries exactly one decision. Changing your mind means
    submitting a new version, which is also what gives the agent something to
    react to; silently overwriting a decision it may already have acted on
    would be worse than refusing.
    """
    if status not in DECIDABLE:
        raise StoreError(f"{status.value!r} is not a decision")
    if version.status.is_decided:
        raise Conflict(
            f"version {version.n} was already {version.status.value}; "
            f"submit a new version to open another round"
        )

    note = (note or "").strip() or None

    # Requesting changes with no feedback at all would hand the agent a
    # revision request it cannot act on.
    if (
        status is ReviewStatus.CHANGES_REQUESTED
        and count_unresolved(conn, version.id) == 0
        and note is None
    ):
        raise StoreError("requesting changes needs at least one open comment or a summary note")

    conn.execute(
        "UPDATE versions SET status = ?, decision_note = ?, decided_at = ? WHERE id = ?",
        (status.value, note, now(), version.id),
    )
    row = conn.execute("SELECT * FROM versions WHERE id = ?", (version.id,)).fetchone()
    return Version.from_row(row)


@dataclass(frozen=True, slots=True)
class DocumentState:
    """Everything an agent needs on resume, in one answer."""

    document: Document
    version: Version
    unresolved: tuple[Comment, ...]

    @property
    def status(self) -> ReviewStatus:
        return self.version.status


def document_state(conn: sqlite3.Connection, slug: str) -> DocumentState:
    document = require_document(conn, slug)
    version = latest_version(conn, document.id)
    if version is None:  # pragma: no cover - documents always have a version
        raise NotFound(f"document {slug!r} has no versions")
    return DocumentState(
        document=document,
        version=version,
        unresolved=tuple(open_comments(conn, version.id)),
    )
