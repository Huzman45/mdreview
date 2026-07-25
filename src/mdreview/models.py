"""Domain types.

These mirror the storage schema. Statuses are enums rather than bare strings so
that the exit-code mapping and the state transitions have a single source of
truth.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import StrEnum


class ReviewStatus(StrEnum):
    """The state of one review round, which is to say of one version."""

    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    CANCELLED = "cancelled"

    @property
    def is_decided(self) -> bool:
        return self is not ReviewStatus.PENDING


class CommentState(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    OUTDATED = "outdated"


@dataclass(frozen=True, slots=True)
class Document:
    id: int
    slug: str
    title: str
    project_path: str | None
    session_id: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Document:
        return cls(
            id=row["id"],
            slug=row["slug"],
            title=row["title"],
            project_path=row["project_path"],
            session_id=row["session_id"],
            created_at=row["created_at"],
        )


@dataclass(frozen=True, slots=True)
class Version:
    id: int
    document_id: int
    n: int
    content: str
    content_sha: str
    status: ReviewStatus
    decision_note: str | None
    decided_at: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Version:
        return cls(
            id=row["id"],
            document_id=row["document_id"],
            n=row["n"],
            content=row["content"],
            content_sha=row["content_sha"],
            status=ReviewStatus(row["status"]),
            decision_note=row["decision_note"],
            decided_at=row["decided_at"],
            created_at=row["created_at"],
        )


@dataclass(frozen=True, slots=True)
class Comment:
    id: int
    version_id: int
    ref: str
    line_start: int
    line_end: int
    quoted: str
    body: str
    state: CommentState
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Comment:
        return cls(
            id=row["id"],
            version_id=row["version_id"],
            ref=row["ref"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            quoted=row["quoted"],
            body=row["body"],
            state=CommentState(row["state"]),
            created_at=row["created_at"],
        )
