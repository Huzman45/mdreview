"""Range selection in the rendered view, exercised by a real browser.

The gesture — click anchors, shift-click extends — is pure client behaviour,
so nothing short of a browser can verify it, and the failure mode it guards
(a comment silently anchored to the wrong lines) is the worst one this tool
has. Skipped when the browser is not installed, like the viewport checks.
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

# Line numbers matter here. Blocks and their ranges, as render.py reports
# them: heading 1, paragraph 3, list items 5, 6 and 7-8 (markdown-it folds the
# blank after a list into its last item), paragraph 9, then a nested list
# whose outer item spans 11-14 around inner items 12 and 13-14, paragraph 15.
CONTENT = """# Rollout plan

The first paragraph sets the scene.

- step one
- step two
- step three

A closing paragraph.

- outer step
  - inner one
  - inner two

Done.
"""


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    data = tmp_path_factory.mktemp("selection-data")
    work = tmp_path_factory.mktemp("selection-work")
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


@pytest.fixture(scope="module")
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
    page.wait_for_selector(".mdr-block")
    try:
        yield page
    finally:
        context.close()


def block(page, start: int):
    return page.locator(f'.mdr-block[data-line-start="{start}"]').first


def fields(page) -> tuple[str, str]:
    return (
        page.locator("#line_start").input_value(),
        page.locator("#line_end").input_value(),
    )


def test_shift_click_extends_downward(page) -> None:
    block(page, 3).click()
    block(page, 9).click(modifiers=["Shift"])
    assert fields(page) == ("3", "9")
    label = page.locator("#selection-label").inner_text().lower()
    # The label genuinely spells its range with an en dash.
    assert "lines 3–9" in label  # noqa: RUF001


def test_shift_click_extends_upward(page) -> None:
    block(page, 9).click()
    block(page, 3).click(modifiers=["Shift"])
    assert fields(page) == ("3", "9")


def painted_starts(page) -> list[str]:
    return page.evaluate(
        """() => [...document.querySelectorAll('.mdr-block.selected')]
             .map(el => el.getAttribute('data-line-start'))"""
    )


def test_intervening_blocks_are_painted(page) -> None:
    block(page, 3).click()
    block(page, 9).click(modifiers=["Shift"])
    # The list element itself is not an anchor block, so its items paint
    # individually — everything the span crosses lights up.
    assert painted_starts(page) == ["3", "5", "6", "7", "9"]


def test_nested_blocks_are_not_double_painted(page) -> None:
    """When a covered list item contains covered items of its own, only the
    outer one is painted; tinting both would read as a heavier selection."""
    # Click the outer item's own first line; its geometric centre falls
    # inside the nested list, where innermost-wins would rightly pick the
    # inner item instead.
    block(page, 11).click(position={"x": 30, "y": 8})
    block(page, 15).click(modifiers=["Shift"])
    assert fields(page) == ("11", "15")
    assert painted_starts(page) == ["11", "15"]
    doubly = page.evaluate(
        """() => [...document.querySelectorAll('.mdr-block.selected')]
             .filter(el => el.parentElement.closest('.mdr-block.selected')).length"""
    )
    assert doubly == 0


def test_partially_covered_containers_are_not_painted(page) -> None:
    """A span over the inner items only must not light the outer item that
    also holds lines outside the span."""
    block(page, 12).click()
    block(page, 13).click(modifiers=["Shift"])
    assert fields(page) == ("12", "14")
    assert painted_starts(page) == ["12", "13"]


def test_plain_click_starts_over(page) -> None:
    block(page, 3).click()
    block(page, 9).click(modifiers=["Shift"])
    block(page, 5).click()
    assert fields(page) == ("5", "5")
    assert page.locator(".mdr-block.selected").count() == 1


def test_shift_click_without_an_anchor_selects_one_block(page) -> None:
    block(page, 3).click(modifiers=["Shift"])
    assert fields(page) == ("3", "3")


def test_escape_clears_an_extended_selection(page) -> None:
    block(page, 3).click()
    block(page, 9).click(modifiers=["Shift"])
    page.keyboard.press("Escape")
    assert page.locator(".mdr-block.selected").count() == 0
    assert fields(page) == ("", "")


def test_a_comment_submitted_from_a_span_anchors_to_it(page, live: str) -> None:
    block(page, 5).click()
    block(page, 7).click(modifiers=["Shift"])
    page.locator("#comment-body").fill("all three steps are one deploy")
    page.locator("#comment-submit").click()
    page.wait_for_selector(".note")

    comments = httpx.get(f"{live}/api/documents/plan/versions/1/comments", timeout=10).json()
    spans = [(c["line_start"], c["line_end"]) for c in comments]
    # The last item's range folds in the blank line after the list (an
    # upstream token.map property, identical for a single click on it), so
    # the span ends at 8 and the quote carries the whole list.
    assert (5, 8) in spans
    added = next(c for c in comments if (c["line_start"], c["line_end"]) == (5, 8))
    assert added["quoted"] == "- step one\n- step two\n- step three\n"
