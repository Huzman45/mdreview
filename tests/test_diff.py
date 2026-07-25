from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview import diff
from mdreview.config import Settings
from mdreview.diff import RowKind
from mdreview.server import create_app


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def kinds(result: diff.Diff) -> list[str]:
    return [row.kind.value for row in result.rows]


# -- classification ---------------------------------------------------------


def test_added_lines_are_classified() -> None:
    result = diff.compare("a\n", "a\nb\n")
    assert result.added == 1
    assert result.removed == 0
    assert "added" in kinds(result)


def test_removed_lines_are_classified() -> None:
    result = diff.compare("a\nb\n", "a\n")
    assert result.removed == 1
    assert result.added == 0
    assert "removed" in kinds(result)


def test_a_replacement_is_both_added_and_removed() -> None:
    result = diff.compare("one\n", "two\n")
    assert result.added == 1
    assert result.removed == 1
    texts = {(r.kind.value, r.text) for r in result.rows}
    assert ("removed", "one") in texts
    assert ("added", "two") in texts


def test_unchanged_lines_are_context() -> None:
    result = diff.compare("keep\nold\n", "keep\nnew\n")
    context = [r for r in result.rows if r.kind is RowKind.CONTEXT]
    assert [r.text for r in context] == ["keep"]


def test_identical_content_reports_nothing_changed() -> None:
    result = diff.compare("same\ncontent\n", "same\ncontent\n")
    assert result.is_empty
    assert result.rows == ()


def test_line_numbers_belong_to_the_correct_side() -> None:
    result = diff.compare("a\nb\n", "a\nB\n")
    removed = next(r for r in result.rows if r.kind is RowKind.REMOVED)
    added = next(r for r in result.rows if r.kind is RowKind.ADDED)
    assert removed.old_line == 2
    assert removed.new_line is None
    assert added.new_line == 2
    assert added.old_line is None


def test_context_rows_carry_both_line_numbers() -> None:
    result = diff.compare("a\nb\n", "a\nB\n")
    context = next(r for r in result.rows if r.kind is RowKind.CONTEXT)
    assert context.old_line == 1
    assert context.new_line == 1


def test_long_unchanged_stretches_are_collapsed() -> None:
    old = "\n".join(["x"] * 40) + "\nend\n"
    new = "\n".join(["x"] * 40) + "\nEND\n"
    result = diff.compare(old, new, context=3)
    assert RowKind.SKIP.value in kinds(result)
    skip = next(r for r in result.rows if r.kind is RowKind.SKIP)
    assert "unchanged lines" in skip.text


def test_short_unchanged_stretches_are_not_collapsed() -> None:
    result = diff.compare("a\nb\nc\nold\n", "a\nb\nc\nnew\n", context=3)
    assert RowKind.SKIP.value not in kinds(result)


def test_markers_match_the_row_kind() -> None:
    result = diff.compare("one\n", "two\n")
    markers = {r.kind.value: r.marker for r in result.rows}
    assert markers["added"] == "+"
    assert markers["removed"] == "-"


def test_empty_to_content() -> None:
    result = diff.compare("", "new\n")
    assert result.added == 1
    assert result.removed == 0


# -- the page ---------------------------------------------------------------


def make_versions(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n\nkeep\nold\n", "source_name": "plan"})
    api.post("/api/documents", json={"content": "# A\n\nkeep\nnew\n", "slug": "plan"})
    api.post("/api/documents", json={"content": "# A\n\nkeep\nnewer\n", "slug": "plan"})


def test_diff_page_shows_changes(api: TestClient) -> None:
    make_versions(api)
    page = api.get("/d/plan/diff/1/2")
    assert page.status_code == 200
    assert "diff-added" in page.text
    assert "diff-removed" in page.text


def test_non_adjacent_versions_compare(api: TestClient) -> None:
    make_versions(api)
    page = api.get("/d/plan/diff/1/3").text
    assert "newer" in page
    assert "old" in page


def test_identical_versions_report_no_change(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "plan"})
    api.post("/api/documents/plan/versions/1/decision", json={"status": "approved"})
    api.post("/api/documents", json={"content": "# A\n", "slug": "plan"})
    assert "Nothing changed" in api.get("/d/plan/diff/1/2").text


def test_diff_is_read_only(api: TestClient) -> None:
    """A comparison belongs to neither version, so nothing can anchor to it."""
    make_versions(api)
    page = api.get("/d/plan/diff/1/2").text
    assert "comment-panel" not in page
    assert "Request changes" not in page


def test_a_revision_links_to_its_comparison(api: TestClient) -> None:
    make_versions(api)
    assert "/d/plan/diff/1/2" in api.get("/d/plan/v/2").text


def test_a_first_version_offers_no_comparison(api: TestClient) -> None:
    make_versions(api)
    assert "/d/plan/diff/" not in api.get("/d/plan/v/1").text


def test_unknown_version_is_404(api: TestClient) -> None:
    make_versions(api)
    assert api.get("/d/plan/diff/1/99").status_code == 404


def test_unknown_document_is_404(api: TestClient) -> None:
    assert api.get("/d/nope/diff/1/2").status_code == 404


def test_diff_escapes_markup(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "plan"})
    api.post(
        "/api/documents",
        json={"content": "# A\n\n<script>alert(1)</script>\n", "slug": "plan"},
    )
    page = api.get("/d/plan/diff/1/2").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
