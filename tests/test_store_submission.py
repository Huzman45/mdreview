from __future__ import annotations

import sqlite3

import pytest

from mdreview import store
from mdreview.models import ReviewStatus
from mdreview.store import StoreError


def test_first_submission_creates_document_and_version(conn: sqlite3.Connection) -> None:
    result = store.submit(conn, content="# Plan\n\nBody\n", source_name="plan")
    assert result.document.slug == "plan"
    assert result.version.n == 1
    assert result.version.status is ReviewStatus.PENDING
    assert result.reused is False


def test_title_is_taken_from_the_first_heading(conn: sqlite3.Connection) -> None:
    result = store.submit(conn, content="# Migration plan\n\nBody\n", source_name="plan")
    assert result.document.title == "Migration plan"


def test_title_falls_back_to_the_source_name(conn: sqlite3.Connection) -> None:
    result = store.submit(conn, content="Just prose, no heading\n", source_name="notes")
    assert result.document.title == "notes"


def test_explicit_title_wins(conn: sqlite3.Connection) -> None:
    result = store.submit(conn, content="# Heading\n", title="Chosen", source_name="plan")
    assert result.document.title == "Chosen"


def test_content_is_stored_verbatim_with_its_digest(conn: sqlite3.Connection) -> None:
    content = "# Plan\n\n- one\n- two\n"
    result = store.submit(conn, content=content, source_name="plan")
    assert result.version.content == content
    assert result.version.content_sha == store.digest(content)


def test_empty_content_is_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(StoreError, match="empty"):
        store.submit(conn, content="   \n\t\n", source_name="plan")
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_revision_creates_the_next_version(conn: sqlite3.Connection) -> None:
    first = store.submit(conn, content="# One\n", source_name="plan")
    second = store.submit(conn, content="# Two\n", slug=first.document.slug, source_name="plan")
    assert second.version.n == 2
    assert second.reused is False


def test_earlier_versions_are_never_rewritten(conn: sqlite3.Connection) -> None:
    first = store.submit(conn, content="# One\n", source_name="plan")
    original_sha = first.version.content_sha
    store.submit(conn, content="# Two\n", slug=first.document.slug, source_name="plan")

    v1 = store.require_version(conn, first.document.id, 1)
    assert v1.content == "# One\n"
    assert v1.content_sha == original_sha


def test_version_numbering_is_per_document(conn: sqlite3.Connection) -> None:
    a = store.submit(conn, content="# A\n", source_name="alpha")
    b = store.submit(conn, content="# B\n", source_name="beta")
    store.submit(conn, content="# A2\n", slug=a.document.slug, source_name="alpha")

    assert [v.n for v in store.list_versions(conn, a.document.id)] == [1, 2]
    assert [v.n for v in store.list_versions(conn, b.document.id)] == [1]


def test_identical_content_against_a_pending_version_is_reused(
    conn: sqlite3.Connection,
) -> None:
    content = "# Plan\n\nBody\n"
    first = store.submit(conn, content=content, source_name="plan")
    again = store.submit(conn, content=content, slug=first.document.slug, source_name="plan")

    assert again.reused is True
    assert again.version.n == 1
    assert len(store.list_versions(conn, first.document.id)) == 1


def test_identical_content_after_a_decision_opens_a_new_round(
    conn: sqlite3.Connection,
) -> None:
    content = "# Plan\n\nBody\n"
    first = store.submit(conn, content=content, source_name="plan")
    conn.execute(
        "UPDATE versions SET status = 'approved', decided_at = ? WHERE id = ?",
        (store.now(), first.version.id),
    )

    again = store.submit(conn, content=content, slug=first.document.slug, source_name="plan")
    assert again.reused is False
    assert again.version.n == 2


def test_slug_collisions_are_suffixed(conn: sqlite3.Connection) -> None:
    first = store.submit(conn, content="# A\n", source_name="plan")
    second = store.submit(conn, content="# B\n", source_name="plan")
    third = store.submit(conn, content="# C\n", source_name="plan")

    assert first.document.slug == "plan"
    assert second.document.slug == "plan-2"
    assert third.document.slug == "plan-3"


def test_provenance_is_recorded(conn: sqlite3.Connection) -> None:
    result = store.submit(
        conn,
        content="# Plan\n",
        project_path="/Users/ferri/projects/sapphire",
        session_id="sess-123",
        source_name="plan",
    )
    assert result.document.project_path == "/Users/ferri/projects/sapphire"
    assert result.document.session_id == "sess-123"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PLAN", "plan"),
        ("My Plan!", "my-plan"),
        ("  spaced  out  ", "spaced-out"),
        ("!!!", "document"),
        ("migration_plan.v2", "migration-plan-v2"),
    ],
)
def test_slugify(raw: str, expected: str) -> None:
    assert store.slugify(raw) == expected


def test_list_documents_returns_latest_version(conn: sqlite3.Connection) -> None:
    a = store.submit(conn, content="# A\n", source_name="alpha")
    store.submit(conn, content="# A2\n", slug=a.document.slug, source_name="alpha")
    store.submit(conn, content="# B\n", source_name="beta")

    summaries = {s.document.slug: s.version.n for s in store.list_documents(conn)}
    assert summaries == {"alpha": 2, "beta": 1}


def test_list_documents_can_filter_to_pending(conn: sqlite3.Connection) -> None:
    a = store.submit(conn, content="# A\n", source_name="alpha")
    store.submit(conn, content="# B\n", source_name="beta")
    conn.execute("UPDATE versions SET status = 'approved' WHERE id = ?", (a.version.id,))

    pending = store.list_documents(conn, pending_only=True)
    assert [s.document.slug for s in pending] == ["beta"]
