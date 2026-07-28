from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview.config import Settings
from mdreview.server import create_app

PLAN = """# Migration plan

Do the thing carefully.

- back up first
- migrate per tenant
"""


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def submit(api: TestClient, content: str = PLAN, **kwargs: object) -> dict:
    payload = {"content": content, "source_name": "plan", **kwargs}
    return api.post("/api/documents", json=payload).json()


def test_document_page_renders_the_markdown(api: TestClient) -> None:
    submit(api)
    page = api.get("/d/plan")
    assert page.status_code == 200
    assert "<h1" in page.text
    assert "Migration plan" in page.text


def test_document_page_reports_state(api: TestClient) -> None:
    submit(api, project_path="/tmp/sapphire")
    text = api.get("/d/plan").text
    assert "pending" in text
    assert "Version 1" in text
    assert "/tmp/sapphire" in text


def test_document_page_carries_block_anchors(api: TestClient) -> None:
    submit(api)
    text = api.get("/d/plan").text
    assert 'data-line-start="1"' in text
    assert "mdr-block" in text


def test_unknown_document_is_404(api: TestClient) -> None:
    assert api.get("/d/nope").status_code == 404


def test_specific_version_is_addressable(api: TestClient) -> None:
    submit(api, content="# One\n")
    submit(api, content="# Two\n", slug="plan")

    assert "One" in api.get("/d/plan/v/1").text
    assert "Two" in api.get("/d/plan/v/2").text
    # The bare slug shows the latest.
    assert "Two" in api.get("/d/plan").text


def test_superseded_version_is_marked(api: TestClient) -> None:
    submit(api, content="# One\n")
    submit(api, content="# Two\n", slug="plan")
    assert "superseded" in api.get("/d/plan/v/1").text
    assert "superseded" not in api.get("/d/plan/v/2").text


def test_unknown_version_is_404(api: TestClient) -> None:
    submit(api)
    assert api.get("/d/plan/v/99").status_code == 404


def test_index_lists_documents(api: TestClient) -> None:
    submit(api, content="# Alpha\n", source_name="alpha")
    submit(api, content="# Beta\n", source_name="beta")

    text = api.get("/").text
    assert "Alpha" in text
    assert "Beta" in text


def test_index_is_empty_when_nothing_submitted(api: TestClient) -> None:
    page = api.get("/").text
    assert "No documents yet" in page
    assert "mdreview submit" in page


def test_index_shows_unresolved_counts(api: TestClient) -> None:
    """The count is the whole point of the index: what is still outstanding."""
    submit(api)
    assert "open" not in api.get("/").text.split("Waiting for you")[1][:400]

    for body in ("one", "two"):
        api.post(
            "/d/plan/v/1/comments",
            data={"line_start": "1", "line_end": "1", "body": body},
        )
    assert "2 open" in api.get("/").text


def test_index_groups_everything_waiting(api: TestClient) -> None:
    submit(api, content="# A\n", source_name="alpha")
    submit(api, content="# B\n", source_name="beta")
    page = api.get("/").text
    assert "Waiting for you" in page
    assert "Decided" not in page  # nothing decided yet


def test_index_says_when_nothing_is_waiting(api: TestClient) -> None:
    submit(api)
    api.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    assert "All caught up" in api.get("/").text


def test_static_assets_are_served(api: TestClient) -> None:
    assert api.get("/static/app.css").status_code == 200
    assert api.get("/static/app.js").status_code == 200
    assert api.get("/static/htmx.min.js").status_code == 200


def test_markup_in_a_document_is_not_executed(api: TestClient) -> None:
    submit(api, content="# Title\n\n<script>alert(1)</script>\n")
    text = api.get("/d/plan").text
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text


def test_markup_in_a_title_is_escaped(api: TestClient) -> None:
    submit(api, content="# <img src=x onerror=alert(1)>\n")
    text = api.get("/d/plan").text
    assert "<img src=x" not in text


def test_home_directory_is_abbreviated_in_the_chrome() -> None:
    from pathlib import Path

    from mdreview.web import display_path

    home = str(Path.home())
    assert display_path(f"{home}/projects/personal/mdreview") == "~/projects/personal/mdreview"
    assert display_path(home) == "~"
    assert display_path("/tmp/sapphire") == "/tmp/sapphire"
    assert display_path(None) == ""


def test_a_sibling_of_home_is_not_abbreviated() -> None:
    """`/Users/ferrier` must not be rewritten just because it shares a prefix."""
    from pathlib import Path

    from mdreview.web import display_path

    assert display_path(str(Path.home()) + "-backup/x") == str(Path.home()) + "-backup/x"


def test_diagram_library_is_only_loaded_when_needed(api: TestClient) -> None:
    """Mermaid is megabytes; a document without diagrams must not pay for it."""
    api.post("/api/documents", json={"content": PLAN, "source_name": "plain"})
    assert "diagrams.js" not in api.get("/d/plain").text

    api.post(
        "/api/documents",
        json={"content": "# D\n\n```mermaid\ngraph TD;\n  A-->B;\n```\n", "source_name": "dia"},
    )
    page = api.get("/d/dia").text
    assert "diagrams.js" in page
    assert 'data-diagram="mermaid"' in page


def test_diagram_library_is_served_locally(api: TestClient) -> None:
    assert api.get("/static/mermaid.min.js").status_code == 200
    assert api.get("/static/diagrams.js").status_code == 200


# -- theme ------------------------------------------------------------------


def test_theme_control_is_present_on_every_page(api: TestClient) -> None:
    submit(api)
    for path in ("/", "/d/plan"):
        page = api.get(path).text
        assert 'data-theme-choice="light"' in page
        assert 'data-theme-choice="dark"' in page
        assert 'data-theme-choice="system"' in page


def test_theme_script_is_inlined_before_the_stylesheet(api: TestClient) -> None:
    """Applying the stored scheme after paint would flash the wrong colours."""
    page = api.get("/").text
    assert "mdreview-theme" in page
    assert page.index("mdreview-theme") < page.index('href="/static/app.css"')


def test_stylesheet_defines_dark_tokens_once(api: TestClient) -> None:
    """Dark tokens in both a media query and an attribute selector can drift."""
    css = api.get("/static/app.css").text
    assert css.count("--paper: #16140f") == 1
    assert ':root[data-theme="dark"]' in css
    assert "prefers-color-scheme: dark" not in css


def test_task_items_are_not_flex_containers(api: TestClient) -> None:
    """Flex makes every inline child its own flex item, so an inline <code>
    span inside a task item fragments the text into separate wrapped pieces."""
    css = api.get("/static/app.css").text
    block = css[css.index("li.task-list-item") :]
    block = block[: block.index("}")]
    assert "display: block" in block
    assert "flex" not in block


def test_the_title_is_not_printed_twice(api: TestClient) -> None:
    """The document's own heading is the headline; the colophon must not repeat it."""
    submit(api, content="# Migration plan\n\nBody.\n")
    page = api.get("/d/plan").text
    assert page.count("Migration plan") == 2  # <title> and the document's h1
    assert 'class="doc-title"' not in page


def test_a_document_without_a_heading_still_shows_its_title(api: TestClient) -> None:
    submit(api, content="Just prose, no heading at all.\n", source_name="untitled")
    page = api.get("/d/untitled").text
    assert 'class="doc-title"' in page
    assert "untitled" in page


def test_the_source_view_always_shows_the_title(api: TestClient) -> None:
    """No heading is rendered there, so the colophon title is the only one."""
    submit(api, content="# Migration plan\n\nBody.\n")
    assert 'class="doc-title"' in api.get("/d/plan/v/1/raw").text
