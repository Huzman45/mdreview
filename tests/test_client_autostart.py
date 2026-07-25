"""Autostart is what lets the tool work without a daemon, so it is tested for real.

These tests spawn actual server processes on ephemeral ports against a temporary
data directory. The ``managed`` fixture guarantees they are reaped, because a
test suite that leaks background servers is worse than one that fails.
"""

from __future__ import annotations

import contextlib
import os
import signal
import time
from collections.abc import Iterator

import pytest

from mdreview.client import ApiUnreachable, Client
from mdreview.config import Settings


@pytest.fixture
def managed(settings: Settings) -> Iterator[Client]:
    client = Client(settings)
    try:
        yield client
    finally:
        _terminate(client)
        client.close()


def _terminate(client: Client) -> None:
    """Kill the server this client is pointed at, if one is running."""
    try:
        pid = client.get("/healthz").get("pid")
    except Exception:
        return
    if not pid:
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.kill(int(pid), signal.SIGTERM)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not client.is_up():
            return
        time.sleep(0.05)


def test_autostart_launches_a_server_when_none_is_running(managed: Client) -> None:
    assert not managed.is_up()
    managed.ensure_up()
    assert managed.is_up()
    assert managed.get("/healthz")["status"] == "ok"


def test_autostart_is_not_repeated_when_a_server_is_reachable(managed: Client) -> None:
    managed.ensure_up()

    spawns = 0
    original = managed._spawn

    def counting_spawn() -> None:
        nonlocal spawns
        spawns += 1
        original()

    managed._spawn = counting_spawn  # type: ignore[method-assign]
    managed.ensure_up()
    assert spawns == 0


def test_autostarted_server_serves_the_isolated_database(
    managed: Client, settings: Settings
) -> None:
    managed.ensure_up()
    assert settings.database.exists()


def test_disabled_autostart_reports_unreachable(settings: Settings) -> None:
    with (
        Client(settings, autostart=False) as client,
        pytest.raises(ApiUnreachable, match="no server reachable"),
    ):
        client.ensure_up()
