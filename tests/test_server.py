from __future__ import annotations

from fastapi.testclient import TestClient

from mdreview import __version__
from mdreview.config import Settings
from mdreview.migrations import SCHEMA_VERSION
from mdreview.server import create_app


def test_healthz_reports_versions(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == __version__
    assert payload["schema_version"] == SCHEMA_VERSION


def test_startup_creates_and_migrates_the_database(settings: Settings) -> None:
    assert not settings.database.exists()
    with TestClient(create_app(settings)):
        pass
    assert settings.database.exists()
