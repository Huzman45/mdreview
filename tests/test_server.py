from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mdreview import __version__
from mdreview.config import Settings
from mdreview.migrations import SCHEMA_VERSION
from mdreview.server import create_app, run


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


def test_server_revalidates_a_directly_constructed_lan_setting(tmp_path: Path) -> None:
    settings = Settings(
        host="10.31.41.35",
        port=7391,
        database=tmp_path / "db.sqlite",
        allow_lan=False,
    )
    with pytest.raises(ValueError, match="--allow-lan"):
        run(settings)
