from __future__ import annotations

from pathlib import Path

import pytest

from mdreview import config
from mdreview.config import Settings


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1", "localhost"])
def test_loopback_addresses_are_accepted(host: str) -> None:
    assert config.is_loopback(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.com", "::"])
def test_routable_addresses_are_rejected(host: str) -> None:
    assert not config.is_loopback(host)


def test_require_loopback_refuses_a_routable_bind() -> None:
    with pytest.raises(ValueError, match="no authentication"):
        config.require_loopback("0.0.0.0")


def test_settings_refuse_a_routable_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Settings.load(host="0.0.0.0", port=1234, database=tmp_path / "db.sqlite")


def test_data_dir_honours_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MDREVIEW_DATA_DIR", str(tmp_path / "custom"))
    assert config.data_dir() == tmp_path / "custom"
    assert config.db_path() == tmp_path / "custom" / "db.sqlite"


def test_data_dir_falls_back_to_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MDREVIEW_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert config.data_dir() == tmp_path / "xdg" / "mdreview"


def test_port_override_must_be_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MDREVIEW_PORT", "not-a-port")
    with pytest.raises(ValueError, match="must be an integer"):
        config.default_port()


def test_base_url_uses_host_and_port(tmp_path: Path) -> None:
    settings = Settings(host="127.0.0.1", port=9999, database=tmp_path / "db.sqlite")
    assert settings.base_url == "http://127.0.0.1:9999"
