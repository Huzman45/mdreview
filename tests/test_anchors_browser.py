"""Anchored margin notes, measured in a real browser.

Positions depend on rendered geometry, which is invisible to HTML
assertions; every check here reads bounding boxes. Skipped when the browser
is not installed, like the other browser modules.
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

GAP = 14  # keep in step with anchors.js

# Line geometry this file depends on: heading 1, paragraphs 3 and 5, a fence
# spanning 7-27 (twenty interior lines), list items 29 and 30, closing
# paragraph 32.
FENCE_BODY = "\n".join(f"interior line {n}" for n in range(8, 27))
CONTENT = f"""# Anchored notes

Opening paragraph.

Second paragraph after.

```text
{FENCE_BODY}
```

- item one
- item two

Closing paragraph here.
"""

COMMENTS = [
    (3, "first note on the opener"),
    (3, "second note on the opener"),
    (20, "deep inside the fence"),
    (32, "on the closing paragraph"),
]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    data = tmp_path_factory.mktemp("anchors-data")
    work = tmp_path_factory.mktemp("anchors-work")
    port = free_port()
    env = {**os.environ, "MDREVIEW_DATA_DIR": str(data), "MDREVIEW_PORT": str(port)}

    (work / "PLAN.md").write_text(CONTENT, encoding="utf-8")
    (work / "OTHER.md").write_text(CONTENT, encoding="utf-8")
    for name in ("PLAN.md", "OTHER.md"):
        subprocess.run(
            [sys.executable, "-m", "mdreview", "submit", name, "--no-open"],
            capture_output=True,
            text=True,
            env=env,
            cwd=work,
            timeout=60,
            check=True,
        )

    base = f"http://127.0.0.1:{port}"
    for line, body in COMMENTS:
        httpx.post(
            f"{base}/api/documents/plan/versions/1/comments",
            json={"line_start": line, "line_end": line, "body": body},
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
    page.wait_for_selector(".margin.anchored")
    try:
        yield page
    finally:
        context.close()


def box(page, selector: str) -> dict:
    b = page.locator(selector).bounding_box()
    assert b, f"no box for {selector}"
    return b


def note(page, ref: str) -> dict:
    return box(page, f'.note[data-ref="{ref}"]')


def test_a_note_aligns_with_its_block(page) -> None:
    paragraph = box(page, '.mdr-block[data-line-start="3"]')
    first = note(page, "C1")
    assert abs(first["y"] - paragraph["y"]) < 4, (
        f"note at {first['y']}, paragraph at {paragraph['y']}"
    )


def test_notes_sharing_an_anchor_stack_without_overlap(page) -> None:
    first, second = note(page, "C1"), note(page, "C2")
    assert second["y"] >= first["y"] + first["height"], "C2 must clear C1 entirely"
    assert second["y"] - (first["y"] + first["height"]) == pytest.approx(GAP, abs=3)


def test_a_note_into_a_fence_points_into_it(page) -> None:
    fence = box(page, '.mdr-block[data-line-start="7"]')
    deep = note(page, "C3")
    # Line 20 of a 7-27 fence is ~62% of the way down.
    expected = fence["y"] + fence["height"] * (20 - 7) / 21
    assert deep["y"] == pytest.approx(expected, abs=6), (
        f"note at {deep['y']}, expected near {expected} inside fence "
        f"({fence['y']}..{fence['y'] + fence['height']})"
    )
    assert deep["y"] > fence["y"] + fence["height"] * 0.4


def test_no_two_notes_intersect_and_the_sheet_holds_them(page) -> None:
    boxes = [note(page, ref) for ref in ("C1", "C2", "C3", "C4")]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            no_overlap = a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"]
            assert no_overlap, f"notes intersect: {a} vs {b}"
    margin = box(page, "#sidebar")
    last_bottom = max(b["y"] + b["height"] for b in boxes)
    assert margin["y"] + margin["height"] >= last_bottom - 1


def test_the_idle_form_parks_after_the_last_note(page) -> None:
    form = box(page, "#comment-panel")
    last = note(page, "C4")
    assert form["y"] >= last["y"] + last["height"]


def test_the_form_moves_beside_the_selection(page) -> None:
    target = box(page, '.mdr-block[data-line-start="5"]')
    page.locator('.mdr-block[data-line-start="5"]').click()
    page.wait_for_timeout(300)

    form = box(page, "#comment-panel")
    c2 = note(page, "C2")
    # Its anchor region is occupied by C1/C2, so the form takes the first
    # free position beneath them — never overlapping, never above its anchor.
    expected = max(target["y"], c2["y"] + c2["height"] + GAP)
    assert form["y"] == pytest.approx(expected, abs=4)


def test_narrow_layout_keeps_the_stacked_list(browser, live: str) -> None:
    context = browser.new_context(viewport={"width": 500, "height": 900})
    try:
        page = context.new_page()
        page.goto(live + "/d/plan", wait_until="domcontentloaded")
        page.wait_for_selector(".note")
        positions = page.evaluate(
            """() => [...document.querySelectorAll('.margin .note')]
                 .map(el => getComputedStyle(el).position)"""
        )
        assert positions and all(p == "static" for p in positions)
        prose = page.locator("#rendered").bounding_box()
        margin = page.locator("#sidebar").bounding_box()
        assert margin["y"] >= prose["y"] + prose["height"], "margin must sit below the prose"
    finally:
        context.close()


def test_source_view_anchors_to_the_exact_line(browser, live: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    try:
        page = context.new_page()
        page.goto(live + "/d/plan/v/1/raw", wait_until="domcontentloaded")
        page.wait_for_selector(".margin.anchored")
        line = page.locator('.mdr-line[data-line="20"]').bounding_box()
        deep = page.locator('.note[data-ref="C3"]').bounding_box()
        assert deep["y"] == pytest.approx(line["y"], abs=4), (
            f"note at {deep['y']}, line 20 at {line['y']}"
        )
    finally:
        context.close()


def test_hovering_a_note_highlights_its_passage(page) -> None:
    page.locator('.note[data-ref="C3"]').hover()
    page.wait_for_timeout(150)
    referenced = page.locator(".mdr-block.referenced")
    assert referenced.count() == 1
    assert referenced.get_attribute("data-line-start") == "7"

    page.locator("h1").hover()
    page.wait_for_timeout(150)
    assert page.locator(".referenced").count() == 0


def test_a_note_added_through_the_form_lands_anchored(browser, live: str) -> None:
    """After the htmx swap the fresh note must be positioned, not piled at
    the container top."""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    try:
        page = context.new_page()
        page.goto(live + "/d/other", wait_until="domcontentloaded")
        page.wait_for_selector(".margin")
        page.locator('.mdr-block[data-line-start="32"]').click()
        page.locator("#comment-body").fill("a fresh note")
        page.locator("#comment-submit").click()
        page.wait_for_selector('.note[data-ref="C1"]')
        page.wait_for_timeout(300)

        target = page.locator('.mdr-block[data-line-start="32"]').bounding_box()
        fresh = page.locator('.note[data-ref="C1"]').bounding_box()
        assert fresh["y"] == pytest.approx(target["y"], abs=4)
    finally:
        context.close()
