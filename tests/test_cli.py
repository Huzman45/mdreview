"""The exit-code contract is the agent-facing API, so it is exercised for real.

These tests run the CLI against a live server on an ephemeral port with an
isolated data directory, rather than mocking the transport, because the thing
being verified is the process exit status.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from mdreview.client import Client
from mdreview.config import Settings
from mdreview.exits import Exit

PLAN = "# Plan\n\nFirst paragraph.\n\n- alpha\n- beta\n"


@pytest.fixture
def cli(settings: Settings, data_dir: Path, tmp_path: Path) -> Iterator[CliRunner]:
    runner = CliRunner(settings, data_dir, tmp_path)
    try:
        yield runner
    finally:
        runner.shutdown()


class CliRunner:
    def __init__(self, settings: Settings, data_dir: Path, tmp_path: Path) -> None:
        self.settings = settings
        self.workdir = tmp_path / "work"
        self.workdir.mkdir(exist_ok=True)
        self.env = {
            **os.environ,
            "MDREVIEW_DATA_DIR": str(data_dir),
            "MDREVIEW_PORT": str(settings.port),
        }

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "mdreview", *args],
            capture_output=True,
            text=True,
            env=self.env,
            cwd=self.workdir,
            timeout=60,
        )

    def write(self, name: str, content: str) -> Path:
        path = self.workdir / name
        path.write_text(content)
        return path

    def api(self) -> Client:
        return Client(self.settings)

    def shutdown(self) -> None:
        with self.api() as client:
            try:
                pid = client.get("/healthz").get("pid")
            except Exception:
                return
            if not pid:
                return
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(int(pid), signal.SIGTERM)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and client.is_up():
                time.sleep(0.05)


# -- submit -----------------------------------------------------------------


def test_submit_prints_the_url_and_exits_zero(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    result = cli.run("submit", "PLAN.md", "--no-open")
    assert result.returncode == Exit.OK
    assert "plan v1" in result.stdout
    assert "/d/plan" in result.stdout


def test_submit_reports_a_missing_file(cli: CliRunner) -> None:
    result = cli.run("submit", "nope.md", "--no-open")
    assert result.returncode == Exit.ERROR
    assert "no such file" in result.stderr


def test_submit_json_mode(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    result = cli.run("submit", "PLAN.md", "--no-open", "--json")
    payload = json.loads(result.stdout)
    assert payload["slug"] == "plan"
    assert payload["version"] == 1


def test_submit_records_the_working_directory(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    result = cli.run("list", "--json")
    assert str(cli.workdir) in json.loads(result.stdout)[0]["project_path"]


# -- exit codes -------------------------------------------------------------


def test_review_of_a_pending_document_exits_three(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")

    result = cli.run("review", "plan")
    assert result.returncode == Exit.PENDING
    assert "No decision has been recorded yet" in result.stdout
    assert "STATUS: pending" in result.stdout


def test_review_of_an_approved_document_exits_zero(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    with cli.api() as client:
        client.post("/api/documents/plan/versions/1/decision", json={"status": "approved"})

    result = cli.run("review", "plan")
    assert result.returncode == Exit.OK
    assert "STATUS: approved" in result.stdout


def test_review_of_changes_requested_exits_two_with_comments(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    with cli.api() as client:
        client.post(
            "/api/documents/plan/versions/1/comments",
            json={"line_start": 5, "line_end": 5, "body": "wrong bullet"},
        )
        client.post(
            "/api/documents/plan/versions/1/decision",
            json={"status": "changes_requested"},
        )

    result = cli.run("review", "plan")
    assert result.returncode == Exit.CHANGES_REQUESTED
    assert "[C1] L5" in result.stdout
    assert "  > - alpha" in result.stdout
    assert "wrong bullet" in result.stdout


def test_review_of_a_cancelled_document_exits_four(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    with cli.api() as client:
        client.post("/api/documents/plan/versions/1/decision", json={"status": "cancelled"})

    result = cli.run("review", "plan")
    assert result.returncode == Exit.CANCELLED


def test_review_json_preserves_the_exit_code(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")

    result = cli.run("review", "plan", "--json")
    assert result.returncode == Exit.PENDING
    assert json.loads(result.stdout)["status"] == "pending"


def test_review_of_an_unknown_document_errors(cli: CliRunner) -> None:
    cli.run("list")  # start the server
    result = cli.run("review", "nope")
    assert result.returncode == Exit.ERROR
    assert "no document" in result.stderr


def test_unreachable_api_exits_five(settings: Settings, tmp_path: Path) -> None:
    """A dead server must never look like a review verdict.

    Exit 5 is deliberately outside the range of review outcomes so an agent
    cannot read an infrastructure failure as an answer.
    """
    env = {
        **os.environ,
        "MDREVIEW_DATA_DIR": str(tmp_path / "data"),
        "MDREVIEW_PORT": str(settings.port),
        "MDREVIEW_AUTOSTART": "0",
    }
    result = subprocess.run(
        [sys.executable, "-m", "mdreview", "review", "plan"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=60,
    )
    assert result.returncode == Exit.UNREACHABLE
    assert "no server reachable" in result.stderr


def test_unreachable_is_distinct_from_every_review_outcome() -> None:
    outcomes = {Exit.OK, Exit.CHANGES_REQUESTED, Exit.PENDING, Exit.CANCELLED}
    assert Exit.UNREACHABLE not in outcomes


# -- resolve / list / status ------------------------------------------------


def test_resolve_reports_remaining(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    with cli.api() as client:
        for body in ("one", "two"):
            client.post(
                "/api/documents/plan/versions/1/comments",
                json={"line_start": 1, "line_end": 1, "body": body},
            )

    result = cli.run("resolve", "plan", "C1")
    assert result.returncode == Exit.OK
    assert "resolved C1" in result.stdout
    assert "1 unresolved remaining" in result.stdout


def test_resolve_an_unknown_reference_errors(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    result = cli.run("resolve", "plan", "C9")
    assert result.returncode == Exit.ERROR


def test_list_pending(cli: CliRunner) -> None:
    cli.write("A.md", "# Alpha\n")
    cli.write("B.md", "# Beta\n")
    cli.run("submit", "A.md", "--no-open")
    cli.run("submit", "B.md", "--no-open")
    with cli.api() as client:
        client.post("/api/documents/a/versions/1/decision", json={"status": "approved"})

    result = cli.run("list", "--pending", "--json")
    assert [item["slug"] for item in json.loads(result.stdout)] == ["b"]


def test_list_when_empty(cli: CliRunner) -> None:
    result = cli.run("list")
    assert "No documents." in result.stdout


def test_status_prints_one_line(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    result = cli.run("status", "plan")
    assert result.returncode == Exit.OK
    assert result.stdout.strip() == "STATUS: pending   VERSION: 1   UNRESOLVED: 0"


def test_version_flag(cli: CliRunner) -> None:
    from mdreview import __version__

    result = cli.run("--version")
    assert result.returncode == Exit.OK
    assert __version__ in result.stdout


# -- the whole loop ---------------------------------------------------------


def test_the_full_review_loop(cli: CliRunner) -> None:
    """Submit, get changes requested, revise, resubmit, approve."""
    path = cli.write("PLAN.md", PLAN)
    assert cli.run("submit", "PLAN.md", "--no-open").returncode == Exit.OK

    with cli.api() as client:
        client.post(
            "/api/documents/plan/versions/1/comments",
            json={"line_start": 5, "line_end": 5, "body": "not alpha"},
        )
        client.post(
            "/api/documents/plan/versions/1/decision",
            json={"status": "changes_requested"},
        )

    assert cli.run("review", "plan").returncode == Exit.CHANGES_REQUESTED

    cli.run("resolve", "plan", "C1")
    path.write_text("# Plan\n\nFirst paragraph.\n\n- gamma\n- beta\n")
    assert cli.run("submit", "PLAN.md", "--slug", "plan", "--no-open").returncode == Exit.OK

    # A new round is open, so the agent must not proceed.
    assert cli.run("review", "plan").returncode == Exit.PENDING

    with cli.api() as client:
        client.post(
            "/api/documents/plan/versions/2/decision",
            json={"status": "approved", "note": "good now"},
        )

    final = cli.run("review", "plan")
    assert final.returncode == Exit.OK
    assert "STATUS: approved" in final.stdout
    assert "NOTE: good now" in final.stdout
