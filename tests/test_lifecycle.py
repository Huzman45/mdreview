"""Archiving, restoring, and deleting whole documents."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview import store
from mdreview.config import Settings
from mdreview.models import ReviewStatus
from mdreview.server import create_app
from mdreview.store import NotFound

PLAN = "# Plan\n\nFirst paragraph.\n\n- alpha\n- beta\n"


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


# -- archive ----------------------------------------------------------------


def test_archiving_stamps_and_hides_from_the_active_list(conn: sqlite3.Connection) -> None:
    store.submit(conn, content=PLAN, source_name="plan")
    archived = store.archive_document(conn, "plan")
    assert archived.is_archived
    assert archived.archived_at is not None

    assert store.list_documents(conn) == []
    assert [s.document.slug for s in store.list_documents(conn, archived=True)] == ["plan"]
    assert store.count_archived(conn) == 1


def test_archiving_a_pending_document_cancels_its_round(conn: sqlite3.Connection) -> None:
    submission = store.submit(conn, content=PLAN, source_name="plan")
    store.archive_document(conn, "plan")

    version = store.require_version(conn, submission.document.id, 1)
    assert version.status is ReviewStatus.CANCELLED
    assert version.decision_note == store.ARCHIVE_NOTE


def test_archiving_a_decided_document_changes_no_decision(conn: sqlite3.Connection) -> None:
    submission = store.submit(conn, content=PLAN, source_name="plan")
    store.decide(conn, version=submission.version, status=ReviewStatus.APPROVED, note="ship")
    store.archive_document(conn, "plan")

    version = store.require_version(conn, submission.document.id, 1)
    assert version.status is ReviewStatus.APPROVED
    assert version.decision_note == "ship"


def test_archiving_twice_is_idempotent(conn: sqlite3.Connection) -> None:
    store.submit(conn, content=PLAN, source_name="plan")
    first = store.archive_document(conn, "plan")
    again = store.archive_document(conn, "plan")
    assert again.archived_at == first.archived_at


def test_unarchive_restores_the_document_as_left(conn: sqlite3.Connection) -> None:
    submission = store.submit(conn, content=PLAN, source_name="plan")
    store.decide(conn, version=submission.version, status=ReviewStatus.APPROVED)
    store.archive_document(conn, "plan")

    restored = store.unarchive_document(conn, "plan")
    assert not restored.is_archived
    assert [s.document.slug for s in store.list_documents(conn)] == ["plan"]
    version = store.require_version(conn, submission.document.id, 1)
    assert version.status is ReviewStatus.APPROVED


def test_resubmission_reactivates_an_archived_document(conn: sqlite3.Connection) -> None:
    store.submit(conn, content=PLAN, source_name="plan")
    store.archive_document(conn, "plan")

    store.submit(conn, content="# Plan v2\n", slug="plan", source_name="plan")
    summaries = store.list_documents(conn)
    assert [s.document.slug for s in summaries] == ["plan"]
    assert summaries[0].version.status is ReviewStatus.PENDING
    assert store.count_archived(conn) == 0


def test_pending_listing_excludes_archived(conn: sqlite3.Connection) -> None:
    store.submit(conn, content="# A\n", source_name="alpha")
    store.submit(conn, content="# B\n", source_name="beta")
    store.archive_document(conn, "alpha")

    pending = store.list_documents(conn, pending_only=True)
    assert [s.document.slug for s in pending] == ["beta"]


# -- delete -----------------------------------------------------------------


def test_delete_cascades_to_versions_and_comments(conn: sqlite3.Connection) -> None:
    submission = store.submit(conn, content=PLAN, source_name="plan")
    store.create_comment(conn, version=submission.version, line_start=1, line_end=1, body="x")

    store.delete_document(conn, "plan")

    with pytest.raises(NotFound):
        store.require_document(conn, "plan")
    assert conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 0


def test_delete_unknown_slug_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFound):
        store.delete_document(conn, "ghost")


# -- api --------------------------------------------------------------------


def test_api_delete_returns_204_and_removes(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.delete("/api/documents/plan")
    assert response.status_code == 204
    assert api.get("/api/documents/plan").status_code == 404


def test_api_delete_unknown_is_404(api: TestClient) -> None:
    assert api.delete("/api/documents/ghost").status_code == 404


def test_api_list_filters_archived(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "alpha"})
    api.post("/api/documents", json={"content": "# B\n", "source_name": "beta"})
    api.post("/d/alpha/archive")

    active = api.get("/api/documents").json()
    assert [d["slug"] for d in active] == ["beta"]
    archived = api.get("/api/documents", params={"archived": True}).json()
    assert [d["slug"] for d in archived] == ["alpha"]
    pending = api.get("/api/documents", params={"pending": True}).json()
    assert [d["slug"] for d in pending] == ["beta"]


# -- browser ----------------------------------------------------------------


def test_index_offers_archive_and_hides_archived(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "alpha"})
    api.post("/api/documents", json={"content": "# B\n", "source_name": "beta"})

    page = api.get("/").text
    assert 'action="/d/alpha/archive"' in page

    archive = api.post("/d/alpha/archive", follow_redirects=False)
    assert archive.status_code == 303
    assert archive.headers["location"] == "/"

    page = api.get("/").text
    assert "/d/alpha" not in page.split("archived")[0]
    assert "1 archived" in page


def test_archived_page_lists_and_restores(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "alpha"})
    api.post("/d/alpha/archive")

    shelf = api.get("/archived").text
    assert "/d/alpha" in shelf
    assert 'action="/d/alpha/unarchive"' in shelf
    assert "Restore" in shelf

    restore = api.post("/d/alpha/unarchive", follow_redirects=False)
    assert restore.status_code == 303
    assert restore.headers["location"] == "/archived"

    page = api.get("/").text
    assert "/d/alpha" in page
    assert "Nothing archived" in api.get("/archived").text


def test_archived_document_pages_stay_readable(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/d/plan/archive")
    page = api.get("/d/plan")
    assert page.status_code == 200
    assert "First paragraph." in page.text


def test_archiving_a_pending_document_reads_as_cancelled_to_the_agent(
    api: TestClient,
) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/d/plan/archive")
    state = api.get("/api/documents/plan/state").json()
    assert state["status"] == "cancelled"
    assert state["decision_note"] == store.ARCHIVE_NOTE


def test_archive_of_unknown_slug_is_404(api: TestClient) -> None:
    assert api.post("/d/ghost/archive").status_code == 404
    assert api.post("/d/ghost/unarchive").status_code == 404
