"""The whole loop, exercised the way it is actually used.

The CLI is driven as a subprocess and the review is performed through the same
HTTP form posts the browser sends, so both halves of the tool are covered by
one test rather than each being verified in isolation.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from mdreview.client import Client
from mdreview.config import Settings
from mdreview.exits import Exit

PLAN = """# Migration plan

Move the ledger tables without downtime.

- Take a backup
- Migrate in one shot
- Verify row counts
"""

REVISED = """# Migration plan

Move the ledger tables without downtime.

- Take a backup
- Migrate per tenant, in batches
- Verify row counts
"""


@pytest.fixture
def live(settings: Settings, data_dir: Path, tmp_path: Path) -> Iterator[Harness]:
    harness = Harness(settings, data_dir, tmp_path)
    try:
        harness.start()
        yield harness
    finally:
        harness.stop()


class Harness:
    def __init__(self, settings: Settings, data_dir: Path, tmp_path: Path) -> None:
        self.settings = settings
        self.workdir = tmp_path / "project"
        self.workdir.mkdir(exist_ok=True)
        self.env = {
            **os.environ,
            "MDREVIEW_DATA_DIR": str(data_dir),
            "MDREVIEW_PORT": str(settings.port),
        }
        self.http = httpx.Client(base_url=settings.base_url, timeout=10.0)

    def start(self) -> None:
        with Client(self.settings) as client:
            client.ensure_up()

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "mdreview", *args],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.workdir,
            timeout=60,
        )

    def browser_post(self, path: str, data: dict[str, str]) -> httpx.Response:
        """Exactly what the htmx form on the page sends."""
        return self.http.post(path, data=data)

    def page(self, path: str) -> str:
        return self.http.get(path).text

    def stop(self) -> None:
        self.http.close()
        with Client(self.settings) as client:
            try:
                pid = client.get("/healthz").get("pid")
            except Exception:
                return
            if pid:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.kill(int(pid), signal.SIGTERM)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and client.is_up():
                    time.sleep(0.05)


def test_the_agent_and_the_human_complete_a_review_together(live: Harness) -> None:
    plan = live.workdir / "PLAN.md"
    plan.write_text(PLAN)

    # 1. The agent submits and is told where to look.
    submitted = live.cli("submit", "PLAN.md", "--no-open")
    assert submitted.returncode == Exit.OK
    assert "/d/plan" in submitted.stdout

    # 2. Nudged too early, the agent must not proceed.
    assert live.cli("review", "plan").returncode == Exit.PENDING

    # 3. The human opens the page and sees an addressable document.
    page = live.page("/d/plan")
    assert "Migration plan" in page
    assert 'data-line-start="6"' in page  # the "migrate in one shot" bullet

    # 4. The human comments on that bullet and requests changes.
    live.browser_post(
        "/d/plan/v/1/comments",
        {"line_start": "6", "line_end": "6", "body": "cannot hold the lock; per tenant"},
    )
    decided = live.browser_post(
        "/d/plan/v/1/decision", {"status": "changes_requested", "note": ""}
    )
    assert "rule-changes_requested" in decided.text

    # 5. The agent reads the outcome, with the source it refers to.
    review = live.cli("review", "plan")
    assert review.returncode == Exit.CHANGES_REQUESTED
    assert "[C1] L6" in review.stdout
    assert "  > - Migrate in one shot" in review.stdout
    assert "cannot hold the lock" in review.stdout

    # 6. The agent revises, resolves, and resubmits.
    assert live.cli("resolve", "plan", "C1").returncode == Exit.OK
    plan.write_text(REVISED)
    assert live.cli("submit", "PLAN.md", "--slug", "plan", "--no-open").returncode == Exit.OK

    # A fresh round is open, so it still must not proceed.
    assert live.cli("review", "plan").returncode == Exit.PENDING

    # 7. The human approves version 2.
    approved = live.browser_post(
        "/d/plan/v/2/decision", {"status": "approved", "note": "good now"}
    )
    assert "rule-approved" in approved.text

    # 8. The agent proceeds.
    final = live.cli("review", "plan")
    assert final.returncode == Exit.OK
    assert "STATUS: approved" in final.stdout
    assert "NOTE: good now" in final.stdout


def test_history_survives_a_server_restart(live: Harness) -> None:
    live.workdir.joinpath("PLAN.md").write_text(PLAN)
    live.cli("submit", "PLAN.md", "--no-open")
    live.browser_post(
        "/d/plan/v/1/comments", {"line_start": "1", "line_end": "1", "body": "note"}
    )

    live.stop()
    live.http = httpx.Client(base_url=live.settings.base_url, timeout=10.0)
    live.start()

    assert live.cli("status", "plan").stdout.strip().startswith("STATUS: pending")
    assert "note" in live.page("/d/plan")


def test_a_retried_submit_does_not_discard_review_work(live: Harness) -> None:
    """The failure this guards against is silent and expensive."""
    plan = live.workdir / "PLAN.md"
    plan.write_text(PLAN)
    live.cli("submit", "PLAN.md", "--no-open")

    live.browser_post(
        "/d/plan/v/1/comments",
        {"line_start": "6", "line_end": "6", "body": "half-written thought"},
    )
    # The agent retries the identical submission.
    live.cli("submit", "PLAN.md", "--slug", "plan", "--no-open")

    page = live.page("/d/plan")
    assert "half-written thought" in page
    assert "note-outdated" not in page


FENCED_PLAN = """# Cutover

Run this during the freeze window.

```sql
BEGIN;
DELETE FROM ledger WHERE id > 0;
COMMIT;
```
"""

FENCED_REVISED = """# Cutover

Run this during the freeze window.

```sql
BEGIN;
DELETE FROM ledger WHERE tenant_id = ? AND id > 0;
COMMIT;
```
"""


def test_a_review_driven_from_the_source_and_diff_views(live: Harness) -> None:
    """The loop using the views added for line-precise feedback.

    The comment targets one line inside a fenced block, which the rendered view
    cannot isolate, and the revision is checked through the diff rather than by
    re-reading the document.
    """
    plan = live.workdir / "CUTOVER.md"
    plan.write_text(FENCED_PLAN)

    assert live.cli("submit", "CUTOVER.md", "--no-open").returncode == Exit.OK

    # The source view lists every line individually.
    raw = live.page("/d/cutover/v/1/raw")
    assert 'data-line="7"' in raw
    assert "DELETE FROM ledger WHERE id &gt; 0;" in raw

    # Comment on one line inside the fence — impossible from the rendered view.
    live.browser_post(
        "/d/cutover/v/1/comments",
        {"line_start": "7", "line_end": "7", "body": "scope this to one tenant"},
    )
    live.browser_post("/d/cutover/v/1/decision", {"status": "changes_requested", "note": ""})

    # The agent gets exactly that line quoted back.
    review = live.cli("review", "cutover")
    assert review.returncode == Exit.CHANGES_REQUESTED
    assert "[C1] L7" in review.stdout
    assert "  > DELETE FROM ledger WHERE id > 0;" in review.stdout

    # Revise and resubmit.
    assert live.cli("resolve", "cutover", "C1").returncode == Exit.OK
    plan.write_text(FENCED_REVISED)
    assert (
        live.cli("submit", "CUTOVER.md", "--slug", "cutover", "--no-open").returncode == Exit.OK
    )

    # The agent resolved it before resubmitting, so it stays resolved rather
    # than being swept to outdated along with anything left open.
    assert "note-resolved" in live.page("/d/cutover/v/1")

    # The diff shows precisely what changed, without re-reading the document.
    diff = live.page("/d/cutover/diff/1/2")
    assert "diff-added" in diff
    assert "diff-removed" in diff
    assert "tenant_id" in diff

    # Approve, and the agent proceeds.
    live.browser_post("/d/cutover/v/2/decision", {"status": "approved", "note": "good"})
    final = live.cli("review", "cutover")
    assert final.returncode == Exit.OK
    assert "STATUS: approved" in final.stdout
