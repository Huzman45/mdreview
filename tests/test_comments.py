from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview import store
from mdreview.config import Settings
from mdreview.models import CommentState
from mdreview.server import create_app
from mdreview.store import NotFound, StoreError

PLAN = "# Plan\n\nFirst paragraph.\n\n- alpha\n- beta\n"


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def a_version(conn: sqlite3.Connection, content: str = PLAN) -> store.Version:
    return store.submit(conn, content=content, source_name="plan").version


# -- creation ---------------------------------------------------------------


def test_comment_is_anchored_and_opens(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    comment = store.create_comment(
        conn, version=version, line_start=1, line_end=1, body="Rename this"
    )
    assert comment.ref == "C1"
    assert (comment.line_start, comment.line_end) == (1, 1)
    assert comment.state is CommentState.OPEN


def test_quoted_source_is_captured_at_creation(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    comment = store.create_comment(
        conn, version=version, line_start=5, line_end=5, body="wrong"
    )
    assert comment.quoted == "- alpha"


def test_out_of_bounds_anchor_is_rejected(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    with pytest.raises(StoreError, match="outside version"):
        store.create_comment(conn, version=version, line_start=1, line_end=999, body="x")
    assert store.list_comments(conn, version.id) == []


def test_empty_body_is_rejected(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    with pytest.raises(StoreError, match="empty comment"):
        store.create_comment(conn, version=version, line_start=1, line_end=1, body="  ")


def test_body_is_trimmed(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    comment = store.create_comment(
        conn, version=version, line_start=1, line_end=1, body="  spaced  "
    )
    assert comment.body == "spaced"


# -- references -------------------------------------------------------------


def test_references_are_assigned_in_creation_order(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    refs = [
        store.create_comment(
            conn, version=version, line_start=1, line_end=1, body=f"note {i}"
        ).ref
        for i in range(3)
    ]
    assert refs == ["C1", "C2", "C3"]


def test_references_restart_per_version(conn: sqlite3.Connection) -> None:
    first = store.submit(conn, content="# One\n", source_name="plan")
    store.create_comment(conn, version=first.version, line_start=1, line_end=1, body="on v1")
    second = store.submit(conn, content="# Two\n", slug=first.document.slug, source_name="plan")
    comment = store.create_comment(
        conn, version=second.version, line_start=1, line_end=1, body="on v2"
    )
    assert comment.ref == "C1"


def test_reference_survives_resolution(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="a")
    store.create_comment(conn, version=version, line_start=3, line_end=3, body="b")
    store.resolve_comment(conn, version.id, "C2")

    refs = [c.ref for c in store.list_comments(conn, version.id)]
    assert refs == ["C1", "C2"]


def test_a_resolved_reference_is_not_reused(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="a")
    store.resolve_comment(conn, version.id, "C1")
    nxt = store.create_comment(conn, version=version, line_start=3, line_end=3, body="b")
    assert nxt.ref == "C2"


# -- lifecycle --------------------------------------------------------------


def test_resolving_closes_a_comment(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="a")
    resolved = store.resolve_comment(conn, version.id, "C1")
    assert resolved.state is CommentState.RESOLVED
    assert store.open_comments(conn, version.id) == []


def test_resolving_is_idempotent(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="a")
    store.resolve_comment(conn, version.id, "C1")
    again = store.resolve_comment(conn, version.id, "C1")
    assert again.state is CommentState.RESOLVED


def test_unknown_reference_is_reported(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    with pytest.raises(NotFound, match="C9"):
        store.resolve_comment(conn, version.id, "C9")


def test_unresolved_count(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="a")
    store.create_comment(conn, version=version, line_start=3, line_end=3, body="b")
    store.resolve_comment(conn, version.id, "C1")
    assert store.count_unresolved(conn, version.id) == 1


# -- superseding ------------------------------------------------------------


def test_a_new_version_outdates_open_comments(conn: sqlite3.Connection) -> None:
    first = store.submit(conn, content=PLAN, source_name="plan")
    store.create_comment(conn, version=first.version, line_start=1, line_end=1, body="a")
    store.create_comment(conn, version=first.version, line_start=3, line_end=3, body="b")

    store.submit(conn, content="# Revised\n", slug=first.document.slug, source_name="plan")

    states = {c.ref: c.state for c in store.list_comments(conn, first.version.id)}
    assert states == {"C1": CommentState.OUTDATED, "C2": CommentState.OUTDATED}


def test_resolved_comments_stay_resolved_across_a_revision(
    conn: sqlite3.Connection,
) -> None:
    first = store.submit(conn, content=PLAN, source_name="plan")
    store.create_comment(conn, version=first.version, line_start=1, line_end=1, body="a")
    store.create_comment(conn, version=first.version, line_start=3, line_end=3, body="b")
    store.resolve_comment(conn, first.version.id, "C1")

    store.submit(conn, content="# Revised\n", slug=first.document.slug, source_name="plan")

    states = {c.ref: c.state for c in store.list_comments(conn, first.version.id)}
    assert states == {"C1": CommentState.RESOLVED, "C2": CommentState.OUTDATED}


def test_anchors_are_never_rewritten_by_a_revision(conn: sqlite3.Connection) -> None:
    first = store.submit(conn, content=PLAN, source_name="plan")
    original = store.create_comment(
        conn, version=first.version, line_start=5, line_end=5, body="a"
    )
    store.submit(conn, content="# Totally different\n\nshorter\n", slug=first.document.slug)

    after = store.get_comment(conn, first.version.id, "C1")
    assert after is not None
    assert (after.line_start, after.line_end) == (original.line_start, original.line_end)
    assert after.quoted == original.quoted == "- alpha"


def test_a_reused_submission_does_not_outdate_comments(conn: sqlite3.Connection) -> None:
    """The retry guard exists precisely to protect in-progress review work."""
    first = store.submit(conn, content=PLAN, source_name="plan")
    store.create_comment(conn, version=first.version, line_start=1, line_end=1, body="a")
    store.submit(conn, content=PLAN, slug=first.document.slug, source_name="plan")

    comment = store.get_comment(conn, first.version.id, "C1")
    assert comment is not None
    assert comment.state is CommentState.OPEN


# -- api --------------------------------------------------------------------


def test_api_create_and_list_comments(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    created = api.post(
        "/api/documents/plan/versions/1/comments",
        json={"line_start": 5, "line_end": 5, "body": "wrong bullet"},
    )
    assert created.status_code == 201
    assert created.json()["ref"] == "C1"
    assert created.json()["quoted"] == "- alpha"

    listed = api.get("/api/documents/plan/versions/1/comments").json()
    assert [c["ref"] for c in listed] == ["C1"]


def test_api_rejects_out_of_bounds_anchor(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/api/documents/plan/versions/1/comments",
        json={"line_start": 1, "line_end": 500, "body": "x"},
    )
    assert response.status_code == 422


def test_api_filters_by_state(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    for body in ("a", "b"):
        api.post(
            "/api/documents/plan/versions/1/comments",
            json={"line_start": 1, "line_end": 1, "body": body},
        )
    api.post("/api/documents/plan/versions/1/resolve", json={"refs": ["C1"]})

    open_only = api.get(
        "/api/documents/plan/versions/1/comments", params={"state": "open"}
    ).json()
    assert [c["ref"] for c in open_only] == ["C2"]


def test_api_resolve_reports_remaining(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    for body in ("a", "b", "c"):
        api.post(
            "/api/documents/plan/versions/1/comments",
            json={"line_start": 1, "line_end": 1, "body": body},
        )
    result = api.post(
        "/api/documents/plan/versions/1/resolve", json={"refs": ["C1", "C2"]}
    ).json()
    assert result["resolved"] == ["C1", "C2"]
    assert result["unresolved_remaining"] == 1


def test_api_resolve_unknown_reference_is_404(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post("/api/documents/plan/versions/1/resolve", json={"refs": ["C9"]})
    assert response.status_code == 404


def test_comments_on_an_unknown_version_are_404(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    assert api.get("/api/documents/plan/versions/9/comments").status_code == 404


# -- browser form -----------------------------------------------------------


def test_form_creates_a_comment_and_returns_the_sidebar(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/d/plan/v/1/comments",
        data={"line_start": "5", "line_end": "5", "body": "not this bullet"},
    )
    assert response.status_code == 200
    assert "not this bullet" in response.text
    assert "C1" in response.text


def test_form_reports_a_missing_selection(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/d/plan/v/1/comments", data={"line_start": "", "line_end": "", "body": "x"}
    )
    assert "Select a block first" in response.text


def test_form_reports_an_empty_body(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/d/plan/v/1/comments", data={"line_start": "1", "line_end": "1", "body": " "}
    )
    assert "empty comment" in response.text


def test_form_resolves_a_comment(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/d/plan/v/1/comments", data={"line_start": "1", "line_end": "1", "body": "x"})
    response = api.post("/d/plan/v/1/comments/C1/resolve")
    assert "comment-resolved" in response.text


def test_comment_markup_is_escaped_on_the_page(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post(
        "/d/plan/v/1/comments",
        data={
            "line_start": "1",
            "line_end": "1",
            "body": '<img src=x onerror="alert(1)">',
        },
    )
    page = api.get("/d/plan").text
    assert "<img src=x" not in page
    assert "&lt;img src=x" in page


def test_superseded_versions_cannot_be_commented_on_from_the_page(
    api: TestClient,
) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/api/documents", json={"content": "# New\n", "slug": "plan"})

    old = api.get("/d/plan/v/1").text
    assert "comment-panel" not in old
    new = api.get("/d/plan/v/2").text
    assert "comment-panel" in new
