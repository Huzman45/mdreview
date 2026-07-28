"""Nothing may be wider than the screen, at any width, on any page.

This exists because the same bug shipped twice. Both times it was a CSS property
that reads fine in isolation — `white-space: nowrap` on inline code — and both
times it pushed real documents hundreds of pixels wider than a phone viewport.
Assertions about markup cannot catch it; only a real layout can.

Skipped when the browser is not installed, so the suite still runs without it:

    uv run playwright install chromium
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright is not installed")

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

# A document that previously triggered the bug: long inline identifiers and a
# table wider than a phone.
CONTENT = """# Ledger shapes

Two tables that every feature reads from: `treasury.transactions` and
`treasury.balances`, keyed on `company_code · account_code · transaction_id · a
very long identifier that cannot be broken at a space`.

| Effort | Where | What it assumed |
| ------ | ----- | --------------- |
| Cash dashboard | thread `#treasury` | a dated balance per account |
| Statement archive | PR #2091 | `bank_statement_transaction` on `(archive_id, seq)` |

```sql
SELECT company_code, account_code FROM treasury.transactions WHERE id > 0;
```
"""

WIDTHS = [390, 834, 1194, 1440]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    data = tmp_path_factory.mktemp("viewport-data")
    work = tmp_path_factory.mktemp("viewport-work")
    port = free_port()
    env = {**os.environ, "MDREVIEW_DATA_DIR": str(data), "MDREVIEW_PORT": str(port)}

    (work / "DOC.md").write_text(CONTENT, encoding="utf-8")

    def cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "mdreview", *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=work,
            timeout=60,
        )

    cli("submit", "DOC.md", "--no-open")
    # A second version, so the diff view has something to render.
    (work / "DOC.md").write_text(CONTENT.replace("Two tables", "Exactly two tables"))
    cli("submit", "DOC.md", "--slug", "doc", "--no-open")

    base = f"http://127.0.0.1:{port}"
    try:
        yield base
    finally:
        import httpx

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


PAGES = [
    ("index", "/"),
    ("rendered", "/d/doc"),
    ("source", "/d/doc/v/2/raw"),
    ("changes", "/d/doc/diff/1/2"),
]


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize(("name", "path"), PAGES, ids=[p[0] for p in PAGES])
def test_nothing_is_wider_than_the_screen(
    browser, live: str, width: int, name: str, path: str
) -> None:
    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        page.goto(live + path, wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        widest = page.evaluate(
            """() => {
                const vw = document.documentElement.clientWidth;
                let worst = null;
                document.querySelectorAll('body *').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.right > vw + 2 && (!worst || r.right > worst.right)) {
                        worst = {tag: el.tagName, cls: String(el.className).slice(0, 40),
                                 right: Math.round(r.right)};
                    }
                });
                return worst;
            }"""
        )
        assert overflow == 0, (
            f"{name} at {width}px overflows by {overflow}px; widest offender: {widest}"
        )
    finally:
        context.close()


def test_the_theme_applies_before_paint(browser, live: str) -> None:
    """A stored preference read after render flashes the wrong colours."""
    context = browser.new_context(viewport={"width": 834, "height": 1194})
    try:
        page = context.new_page()
        page.add_init_script(
            "try { localStorage.setItem('mdreview-theme', 'dark'); } catch (e) {}"
        )
        page.goto(live + "/d/doc", wait_until="commit")
        assert page.get_attribute("html", "data-theme") == "dark"
    finally:
        context.close()


def test_inline_code_can_wrap(browser, live: str) -> None:
    """The specific regression: a long identifier must break rather than push the
    page wider than the screen."""
    context = browser.new_context(viewport={"width": 390, "height": 900})
    try:
        page = context.new_page()
        page.goto(live + "/d/doc", wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        widest = page.evaluate(
            """() => Math.max(...[...document.querySelectorAll('.rendered :not(pre) > code')]
                 .map(el => el.getBoundingClientRect().width), 0)"""
        )
        assert widest <= 390, f"an inline code span is {widest}px wide in a 390px view"
    finally:
        context.close()


def test_the_harness_script_exists() -> None:
    """The screenshot harness is how this interface gets reviewed by eye."""
    assert (Path(__file__).parent.parent / "scripts" / "shots.py").is_file()
