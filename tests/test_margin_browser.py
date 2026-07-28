"""The margin's comment tools, exercised by a real browser.

The edit and delete flows run through htmx swaps, a <details> disclosure and a
native confirm dialog — none of which an HTML-string assertion can see working
together. Skipped when the browser is not installed, like the viewport checks.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import httpx
import pytest

pytest.importorskip("playwright.sync_api", reason="playwright is not installed")

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

CONTENT = """# Rollout plan

The first paragraph sets the scene.

- step one
- step two

A closing paragraph.
"""


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def live(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """A running server holding one pending document with two open comments."""
    data = tmp_path_factory.mktemp("margin-data")
    work = tmp_path_factory.mktemp("margin-work")
    port = free_port()
    env = {**os.environ, "MDREVIEW_DATA_DIR": str(data), "MDREVIEW_PORT": str(port)}

    (work / "PLAN.md").write_text(CONTENT, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "mdreview", "submit", "PLAN.md", "--no-open"],
        capture_output=True,
        text=True,
        env=env,
        cwd=work,
        timeout=60,
        check=True,
    )

    base = f"http://127.0.0.1:{port}"
    for body in ("tighten this", "drop this step"):
        httpx.post(
            f"{base}/api/documents/plan/versions/1/comments",
            json={"line_start": 3, "line_end": 3, "body": body},
            timeout=10,
        ).raise_for_status()

    try:
        yield base
    finally:
        with contextlib.suppress(Exception):
            pid = httpx.get(f"{base}/healthz", timeout=5).json().get("pid")
            if pid:
                os.kill(int(pid), 15)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    with contextlib.suppress(Exception):
                        httpx.get(f"{base}/healthz", timeout=1)
                        time.sleep(0.05)
                        continue
                    break


@pytest.fixture
def browser() -> Iterator[object]:
    with sync_playwright() as p:
        try:
            instance = p.chromium.launch()
        except PlaywrightError as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"chromium is not installed: {exc}")
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page(browser, live: str):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(live + "/d/plan", wait_until="domcontentloaded")
    page.wait_for_selector('.note[data-ref="C1"]')
    try:
        yield page
    finally:
        context.close()


def test_edit_and_delete_share_a_row(page) -> None:
    """The tools are one quiet row under the note, not a stack."""
    note = page.locator('.note[data-ref="C1"]')
    edit = note.locator("summary", has_text="Edit").bounding_box()
    delete = note.locator("button", has_text="Delete").bounding_box()
    assert edit and delete
    assert abs(edit["y"] - delete["y"]) < 3, "Edit and Delete are not on one row"
    assert edit["x"] < delete["x"]


def test_editing_a_comment_from_the_margin(page) -> None:
    note = page.locator('.note[data-ref="C1"]')
    note.locator("summary", has_text="Edit").click()

    field = note.locator("textarea[name=body]")
    assert field.input_value() == "tighten this", "the editor must open on the current body"
    field.fill("tighten this, and name the owner")
    note.locator("button", has_text="Save").click()

    page.wait_for_selector('.note[data-ref="C1"] .note-body')
    refreshed = page.locator('.note[data-ref="C1"]')
    assert refreshed.locator(".note-body").inner_text() == "tighten this, and name the owner"
    # inner_text reflects the head's text-transform, so compare case-blind.
    assert "edited" in refreshed.locator(".note-head").inner_text().lower()
    # The anchor is untouched by an edit.
    assert refreshed.get_attribute("data-line-start") == "3"


def test_deleting_a_comment_asks_first(page) -> None:
    confirmed = []
    page.on("dialog", lambda dialog: (confirmed.append(dialog.message), dialog.accept()))

    page.locator('.note[data-ref="C2"]').locator("button", has_text="Delete").click()
    page.wait_for_timeout(400)

    assert confirmed and "C2" in confirmed[0], "deletion must be confirmed"
    assert page.locator('.note[data-ref="C2"]').count() == 0
    assert page.locator('.note[data-ref="C1"]').count() == 1


def test_declining_the_confirm_keeps_the_comment(page) -> None:
    page.on("dialog", lambda dialog: dialog.dismiss())
    page.locator('.note[data-ref="C2"]').locator("button", has_text="Delete").click()
    page.wait_for_timeout(400)
    assert page.locator('.note[data-ref="C2"]').count() == 1
