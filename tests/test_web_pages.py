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
    assert "v1" in text
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
    assert "Nothing submitted yet" in api.get("/").text


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
