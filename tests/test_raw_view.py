"""The source view exists to reach text that block anchoring cannot isolate."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview.config import Settings
from mdreview.server import create_app

FENCED = """# Plan

Intro paragraph.

```sql
SELECT 1;
DELETE FROM ledger;
SELECT 2;
```
"""


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def submit(api: TestClient, content: str = FENCED, **kwargs: object) -> dict:
    return api.post(
        "/api/documents", json={"content": content, "source_name": "plan", **kwargs}
    ).json()


def test_every_line_is_listed_with_its_number(api: TestClient) -> None:
    submit(api)
    page = api.get("/d/plan/v/1/raw").text
    for n in range(1, len(FENCED.splitlines()) + 1):
        assert f'data-line="{n}"' in page


def test_markdown_is_shown_as_literal_source(api: TestClient) -> None:
    submit(api)
    page = api.get("/d/plan/v/1/raw").text
    assert "# Plan" in page
    # A heading must not have been rendered into an element.
    assert "<h1 data-line-start" not in page


def test_raw_view_reports_document_state(api: TestClient) -> None:
    submit(api, project_path="/tmp/x")
    page = api.get("/d/plan/v/1/raw").text
    assert "Plan" in page
    assert "pending" in page
    assert "Version 1" in page


def test_views_link_to_each_other(api: TestClient) -> None:
    submit(api)
    rendered = api.get("/d/plan/v/1").text
    assert "/d/plan/v/1/raw" in rendered
    raw = api.get("/d/plan/v/1/raw").text
    assert 'href="/d/plan/v/1"' in raw


def test_unknown_document_is_404(api: TestClient) -> None:
    assert api.get("/d/nope/v/1/raw").status_code == 404


def test_unknown_version_is_404(api: TestClient) -> None:
    submit(api)
    assert api.get("/d/plan/v/9/raw").status_code == 404


# -- the point of the whole view --------------------------------------------


def test_a_single_line_inside_a_fence_can_be_commented_on(api: TestClient) -> None:
    """Block anchoring treats a fence as atomic; this is what the view is for."""
    submit(api)
    response = api.post(
        "/d/plan/v/1/comments",
        data={"line_start": "7", "line_end": "7", "body": "never run this"},
    )
    assert response.status_code == 200

    comments = api.get("/api/documents/plan/versions/1/comments").json()
    assert len(comments) == 1
    assert comments[0]["line_start"] == 7
    assert comments[0]["quoted"] == "DELETE FROM ledger;"


def test_a_contiguous_range_can_be_commented_on(api: TestClient) -> None:
    submit(api)
    api.post(
        "/d/plan/v/1/comments",
        data={"line_start": "6", "line_end": "8", "body": "reorder these"},
    )
    comment = api.get("/api/documents/plan/versions/1/comments").json()[0]
    assert (comment["line_start"], comment["line_end"]) == (6, 8)
    assert comment["quoted"] == "SELECT 1;\nDELETE FROM ledger;\nSELECT 2;"


def test_a_raw_comment_is_structurally_identical_to_a_block_comment(
    api: TestClient,
) -> None:
    """The agent must not have to care which view produced the feedback."""
    submit(api)
    api.post("/d/plan/v/1/comments", data={"line_start": "1", "line_end": "1", "body": "block"})
    api.post("/d/plan/v/1/comments", data={"line_start": "7", "line_end": "7", "body": "raw"})

    comments = api.get("/api/documents/plan/versions/1/comments").json()
    assert len(comments) == 2
    assert set(comments[0]) == set(comments[1])
    assert [c["ref"] for c in comments] == ["C1", "C2"]


def test_raw_comments_appear_on_the_rendered_page(api: TestClient) -> None:
    submit(api)
    api.post(
        "/d/plan/v/1/comments", data={"line_start": "7", "line_end": "7", "body": "raw note"}
    )
    assert "raw note" in api.get("/d/plan").text


def test_out_of_bounds_is_still_rejected(api: TestClient) -> None:
    submit(api)
    response = api.post(
        "/d/plan/v/1/comments", data={"line_start": "1", "line_end": "999", "body": "x"}
    )
    assert "outside version" in response.text


# -- lifecycle --------------------------------------------------------------


def test_no_comment_form_on_a_decided_version(api: TestClient) -> None:
    submit(api)
    api.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    assert "comment-panel" not in api.get("/d/plan/v/1/raw").text


def test_no_comment_form_on_a_superseded_version(api: TestClient) -> None:
    submit(api)
    submit(api, content="# Revised\n", slug="plan")
    assert "comment-panel" not in api.get("/d/plan/v/1/raw").text
    assert "comment-panel" in api.get("/d/plan/v/2/raw").text


def test_raw_view_loads_the_line_selection_script(api: TestClient) -> None:
    submit(api)
    assert "rawlines.js" in api.get("/d/plan/v/1/raw").text
    assert "rawlines.js" not in api.get("/d/plan/v/1").text


def test_markup_in_source_is_escaped_in_the_raw_view(api: TestClient) -> None:
    submit(api, content="# T\n\n<script>alert(1)</script>\n")
    page = api.get("/d/plan/v/1/raw").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
