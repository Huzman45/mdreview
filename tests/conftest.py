from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path

import pytest

from mdreview.config import Settings


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate all on-disk state so tests never touch the real database."""
    target = tmp_path / "data"
    target.mkdir()
    monkeypatch.setenv("MDREVIEW_DATA_DIR", str(target))
    return target


@pytest.fixture
def db_file(data_dir: Path) -> Path:
    return data_dir / "db.sqlite"


@pytest.fixture
def settings(db_file: Path) -> Settings:
    return Settings(host="127.0.0.1", port=free_port(), database=db_file)


@pytest.fixture
def conn(db_file: Path) -> Iterator[object]:
    from mdreview import db

    connection = db.connect(db_file)
    db.migrate(connection)
    try:
        yield connection
    finally:
        connection.close()
