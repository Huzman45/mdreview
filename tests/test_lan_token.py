"""The token is what makes a LAN-bound server safe to leave running.

These tests drive the app through a client that can claim an arbitrary peer
address, because the whole guard turns on which address the connection came
from.
"""

from __future__ import annotations

import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mdreview import tokens
from mdreview.config import Settings
from mdreview.server import create_app

LAN_HOST = "10.31.41.35"


@pytest.fixture
def lan_settings(db_file: Path) -> Settings:
    return Settings(host=LAN_HOST, port=7391, database=db_file, allow_lan=True)


@pytest.fixture
def lan(lan_settings: Settings) -> Iterator[TestClient]:
    """A client whose requests appear to arrive from another machine."""
    with TestClient(create_app(lan_settings), client=("192.168.1.50", 51000)) as client:
        yield client


@pytest.fixture
def local(lan_settings: Settings) -> Iterator[TestClient]:
    """A client on the same LAN-bound server, but arriving over loopback."""
    with TestClient(create_app(lan_settings), client=("127.0.0.1", 51000)) as client:
        yield client


# -- storage ----------------------------------------------------------------


def test_token_is_generated_on_first_use(data_dir: Path) -> None:
    assert tokens.read() is None
    value = tokens.ensure()
    assert value
    assert tokens.read() == value


def test_token_has_enough_entropy(data_dir: Path) -> None:
    # 32 random bytes base64url-encoded is comfortably over 128 bits.
    assert len(tokens.ensure()) >= 40


def test_token_file_is_owner_only(data_dir: Path) -> None:
    tokens.ensure()
    mode = tokens.token_path().stat().st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_token_is_stable_across_calls(data_dir: Path) -> None:
    assert tokens.ensure() == tokens.ensure()


def test_rotation_replaces_the_token(data_dir: Path) -> None:
    first = tokens.ensure()
    second = tokens.rotate()
    assert second != first
    assert tokens.matches(second)
    assert not tokens.matches(first)


def test_matches_rejects_empty_and_wrong(data_dir: Path) -> None:
    tokens.ensure()
    assert not tokens.matches(None)
    assert not tokens.matches("")
    assert not tokens.matches("nope")


# -- the guard --------------------------------------------------------------


def test_loopback_needs_no_token(local: TestClient) -> None:
    """The agent issues many requests per review and must not carry a credential."""
    assert local.get("/healthz").status_code == 200
    assert local.get("/").status_code == 200


def test_lan_without_a_token_is_refused(lan: TestClient) -> None:
    response = lan.get("/")
    assert response.status_code == 403


def test_lan_with_a_wrong_token_is_refused(lan: TestClient) -> None:
    assert lan.get("/", params={"t": "wrong"}).status_code == 403


def test_lan_with_the_token_is_served(lan: TestClient, data_dir: Path) -> None:
    assert lan.get("/", params={"t": tokens.ensure()}).status_code == 200


def test_a_valid_token_sets_a_cookie(lan: TestClient, data_dir: Path) -> None:
    response = lan.get("/", params={"t": tokens.ensure()})
    assert tokens.COOKIE_NAME in response.cookies


def test_the_cookie_authorises_later_requests(lan: TestClient, data_dir: Path) -> None:
    lan.get("/", params={"t": tokens.ensure()})
    # No token in the URL this time.
    assert lan.get("/").status_code == 200


def test_a_rotated_token_invalidates_the_old_one(lan: TestClient, data_dir: Path) -> None:
    old = tokens.ensure()
    lan.get("/", params={"t": old})
    tokens.rotate()
    lan.cookies.clear()
    assert lan.get("/", params={"t": old}).status_code == 403


def test_mutating_endpoints_are_protected(lan: TestClient, local: TestClient) -> None:
    local.post("/api/documents", json={"content": "# P\n", "source_name": "plan"})

    comment = lan.post(
        "/d/plan/v/1/comments",
        data={"line_start": "1", "line_end": "1", "body": "sneaky"},
    )
    assert comment.status_code == 403

    decision = lan.post("/d/plan/v/1/decision", data={"status": "approved", "note": ""})
    assert decision.status_code == 403

    # Nothing changed.
    state = local.get("/api/documents/plan/state").json()
    assert state["status"] == "pending"
    assert state["open_comments"] == []


def test_the_api_is_protected_too(lan: TestClient) -> None:
    assert lan.get("/api/documents").status_code == 403


def test_refusal_leaks_nothing(lan: TestClient, local: TestClient) -> None:
    local.post(
        "/api/documents",
        json={"content": "# Secret merger plan\n", "source_name": "secret-merger"},
    )
    body = lan.get("/d/secret-merger").text
    assert "secret-merger" not in body
    assert "Secret merger" not in body


def test_an_unknown_document_is_indistinguishable_from_a_bad_token(
    lan: TestClient,
) -> None:
    """Otherwise an unauthenticated caller could enumerate the store."""
    existing = lan.get("/d/nope")
    missing = lan.get("/d/also-nope")
    assert existing.status_code == missing.status_code == 403
    assert existing.text == missing.text


def test_a_forged_forwarding_header_does_not_grant_loopback(lan: TestClient) -> None:
    """The peer address must come from the connection, never a header."""
    for header in ("X-Forwarded-For", "X-Real-IP", "Forwarded"):
        response = lan.get("/", headers={header: "127.0.0.1"})
        assert response.status_code == 403, header


# -- loopback-only servers are untouched ------------------------------------


def test_a_loopback_server_installs_no_guard(settings: Settings) -> None:
    with TestClient(create_app(settings), client=("192.168.1.50", 51000)) as client:
        # No guard exists at all, so even a non-loopback peer is served. The
        # socket is bound to loopback, so this cannot happen in reality.
        assert client.get("/healthz").status_code == 200
