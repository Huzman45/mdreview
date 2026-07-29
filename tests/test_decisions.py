from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview import store
from mdreview.config import Settings
from mdreview.models import ReviewStatus
from mdreview.server import create_app
from mdreview.store import Conflict, NotFound, StoreError

PLAN = "# Plan\n\nFirst paragraph.\n\n- alpha\n- beta\n"


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def a_version(conn: sqlite3.Connection) -> store.Version:
    return store.submit(conn, content=PLAN, source_name="plan").version


# -- recording --------------------------------------------------------------


def test_approving_sets_status_and_timestamp(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    decided = store.decide(conn, version=version, status=ReviewStatus.APPROVED)
    assert decided.status is ReviewStatus.APPROVED
    assert decided.decided_at is not None


def test_approval_needs_no_comments(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    assert (
        store.decide(conn, version=version, status=ReviewStatus.APPROVED).status
        is ReviewStatus.APPROVED
    )


def test_requesting_changes_with_comments(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="fix")
    decided = store.decide(conn, version=version, status=ReviewStatus.CHANGES_REQUESTED)
    assert decided.status is ReviewStatus.CHANGES_REQUESTED


def test_a_note_is_stored(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    decided = store.decide(
        conn, version=version, status=ReviewStatus.APPROVED, note="  looks good  "
    )
    assert decided.decision_note == "looks good"


def test_requesting_changes_without_feedback_is_refused(
    conn: sqlite3.Connection,
) -> None:
    version = a_version(conn)
    with pytest.raises(StoreError, match="at least one open comment"):
        store.decide(conn, version=version, status=ReviewStatus.CHANGES_REQUESTED)
    assert store.require_version(conn, version.document_id, 1).status is ReviewStatus.PENDING


def test_a_note_alone_is_enough_feedback(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    decided = store.decide(
        conn,
        version=version,
        status=ReviewStatus.CHANGES_REQUESTED,
        note="rewrite the whole thing",
    )
    assert decided.status is ReviewStatus.CHANGES_REQUESTED


def test_deleted_comments_do_not_count_as_feedback(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="fix")
    store.delete_comment(conn, version.id, "C1")
    with pytest.raises(StoreError, match="at least one open comment"):
        store.decide(conn, version=version, status=ReviewStatus.CHANGES_REQUESTED)


def test_a_decided_version_cannot_be_decided_again(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.decide(conn, version=version, status=ReviewStatus.APPROVED)
    refreshed = store.require_version(conn, version.document_id, 1)

    with pytest.raises(Conflict, match="already approved"):
        store.decide(conn, version=refreshed, status=ReviewStatus.CHANGES_REQUESTED)

    assert store.require_version(conn, version.document_id, 1).status is ReviewStatus.APPROVED


def test_pending_is_not_a_decision(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    with pytest.raises(StoreError, match="not a decision"):
        store.decide(conn, version=version, status=ReviewStatus.PENDING)


# -- state ------------------------------------------------------------------


def test_state_of_a_pending_document(conn: sqlite3.Connection) -> None:
    store.submit(conn, content=PLAN, source_name="plan")
    state = store.document_state(conn, "plan")
    assert state.status is ReviewStatus.PENDING
    assert state.open_comments == ()


def test_state_reports_open_comments(conn: sqlite3.Connection) -> None:
    version = a_version(conn)
    store.create_comment(conn, version=version, line_start=1, line_end=1, body="one")
    store.create_comment(conn, version=version, line_start=5, line_end=5, body="two")
    store.delete_comment(conn, version.id, "C1")
    store.decide(conn, version=version, status=ReviewStatus.CHANGES_REQUESTED)

    state = store.document_state(conn, "plan")
    assert state.status is ReviewStatus.CHANGES_REQUESTED
    assert [c.ref for c in state.open_comments] == ["C2"]
    assert state.open_comments[0].quoted == "- alpha"


def test_state_of_an_unknown_document(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFound):
        store.document_state(conn, "nope")


# -- api --------------------------------------------------------------------


def test_api_approve(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post("/api/documents/plan/versions/1/decision", json={"status": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_api_second_decision_conflicts(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/api/documents/plan/versions/1/decision", json={"status": "approved"})
    again = api.post("/api/documents/plan/versions/1/decision", json={"status": "approved"})
    assert again.status_code == 409


def test_api_request_changes_without_feedback_is_422(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/api/documents/plan/versions/1/decision",
        json={"status": "changes_requested"},
    )
    assert response.status_code == 422


def test_api_state_endpoint(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post(
        "/api/documents/plan/versions/1/comments",
        json={"line_start": 5, "line_end": 5, "body": "wrong"},
    )
    api.post(
        "/api/documents/plan/versions/1/decision",
        json={"status": "changes_requested", "note": "see comments"},
    )

    state = api.get("/api/documents/plan/state").json()
    assert state["status"] == "changes_requested"
    assert state["version"] == 1
    assert state["decision_note"] == "see comments"
    assert len(state["open_comments"]) == 1
    assert state["open_comments"][0]["quoted"] == "- alpha"


def test_api_state_unknown_document_is_404(api: TestClient) -> None:
    assert api.get("/api/documents/nope/state").status_code == 404


# -- browser ----------------------------------------------------------------


def test_page_offers_a_decision_while_pending(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    page = api.get("/d/plan").text
    assert "Approve" in page
    assert "Request changes" in page


def test_form_approves(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    assert "rule-approved" in response.text
    assert "Approve" not in response.text


def test_form_refuses_changes_without_feedback(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/d/plan/v/1/decision", data={"status": "changes_requested", "note": ""}
    )
    assert "at least one open comment" in response.text


def test_form_requests_changes_with_a_note(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post(
        "/d/plan/v/1/decision",
        data={"status": "changes_requested", "note": "start over"},
    )
    assert "rule-changes_requested" in response.text
    assert "start over" in response.text


def test_form_rejects_an_unknown_decision(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    response = api.post("/d/plan/v/1/decision", data={"status": "nonsense", "note": ""})
    assert "Unknown decision" in response.text


def test_deciding_twice_from_the_page_conflicts(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    again = api.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    assert again.status_code == 409


def test_a_decided_version_hides_the_comment_form(api: TestClient) -> None:
    api.post("/api/documents", json={"content": PLAN, "source_name": "plan"})
    api.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    page = api.get("/d/plan").text
    assert "comment-panel" not in page


def test_index_distinguishes_pending_from_decided(api: TestClient) -> None:
    """Grouping carries it: a decided document shows its decision and sits under
    Decided rather than among the documents awaiting review."""
    api.post("/api/documents", json={"content": "# A\n", "source_name": "alpha"})
    api.post("/api/documents", json={"content": "# B\n", "source_name": "beta"})
    api.post("/d/alpha/v/1/decision", data={"status": "approved", "note": ""})

    page = api.get("/").text
    assert "Waiting for you" in page
    assert "Decided" in page
    assert "rule-approved" in page

    waiting, decided = page.split("Decided", 1)
    # beta is still awaiting review; alpha has been decided.
    assert "/d/beta" in waiting
    assert "/d/alpha" in decided
    assert "/d/alpha" not in waiting


def test_api_pending_filter_excludes_decided(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "alpha"})
    api.post("/api/documents", json={"content": "# B\n", "source_name": "beta"})
    api.post("/api/documents/alpha/versions/1/decision", json={"status": "approved"})

    pending = api.get("/api/documents", params={"pending": True}).json()
    assert [item["slug"] for item in pending] == ["beta"]
