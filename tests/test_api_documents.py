from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mdreview.config import Settings
from mdreview.server import create_app


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def test_submit_creates_a_document(api: TestClient) -> None:
    response = api.post(
        "/api/documents",
        json={"content": "# Plan\n\nBody\n", "source_name": "plan"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["slug"] == "plan"
    assert payload["version"] == 1
    assert payload["status"] == "pending"
    assert payload["reused"] is False
    assert payload["url"].endswith("/d/plan")


def test_submit_rejects_empty_content(api: TestClient) -> None:
    response = api.post("/api/documents", json={"content": "   ", "source_name": "plan"})
    assert response.status_code == 422
    assert "empty" in response.json()["detail"]


def test_resubmitting_identical_content_reuses_the_round(api: TestClient) -> None:
    body = {"content": "# Plan\n", "source_name": "plan"}
    first = api.post("/api/documents", json=body).json()
    second = api.post("/api/documents", json={**body, "slug": first["slug"]}).json()

    assert second["reused"] is True
    assert second["version"] == 1


def test_resubmitting_changed_content_creates_a_version(api: TestClient) -> None:
    first = api.post(
        "/api/documents", json={"content": "# One\n", "source_name": "plan"}
    ).json()
    second = api.post(
        "/api/documents",
        json={"content": "# Two\n", "slug": first["slug"], "source_name": "plan"},
    ).json()

    assert second["reused"] is False
    assert second["version"] == 2


def test_get_document_reports_latest_and_history(api: TestClient) -> None:
    first = api.post(
        "/api/documents", json={"content": "# One\n", "source_name": "plan"}
    ).json()
    api.post(
        "/api/documents",
        json={"content": "# Two\n", "slug": first["slug"], "source_name": "plan"},
    )

    payload = api.get(f"/api/documents/{first['slug']}").json()
    assert payload["latest"]["n"] == 2
    assert payload["latest"]["status"] == "pending"
    assert payload["versions"] == [1, 2]


def test_get_unknown_document_is_404(api: TestClient) -> None:
    assert api.get("/api/documents/nope").status_code == 404


def test_list_documents_and_pending_filter(api: TestClient) -> None:
    api.post("/api/documents", json={"content": "# A\n", "source_name": "alpha"})
    api.post("/api/documents", json={"content": "# B\n", "source_name": "beta"})

    everything = api.get("/api/documents").json()
    assert {item["slug"] for item in everything} == {"alpha", "beta"}

    pending = api.get("/api/documents", params={"pending": True}).json()
    assert {item["slug"] for item in pending} == {"alpha", "beta"}


def test_provenance_round_trips(api: TestClient) -> None:
    api.post(
        "/api/documents",
        json={
            "content": "# Plan\n",
            "source_name": "plan",
            "project_path": "/tmp/project",
            "session_id": "abc",
        },
    )
    payload = api.get("/api/documents/plan").json()
    assert payload["project_path"] == "/tmp/project"
    assert payload["session_id"] == "abc"
