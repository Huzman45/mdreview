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

    def run(
        self,
        *args: str,
        stdin: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "mdreview", *args],
            capture_output=True,
            text=True,
            env={**self.env, **(env or {})},
            cwd=self.workdir,
            timeout=60,
            input=stdin,
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


# -- list / status ----------------------------------------------------------


def test_resolve_is_not_a_command(cli: CliRunner) -> None:
    """The old bookkeeping step is gone; resubmission is what closes comments.

    An agent following a stale skill should fail loudly here, not silently
    no-op.
    """
    result = cli.run("resolve", "plan", "C1")
    assert result.returncode != Exit.OK


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


# -- await ------------------------------------------------------------------


def test_await_returns_immediately_when_already_decided(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    with cli.api() as client:
        client.post("/api/documents/plan/versions/1/decision", json={"status": "approved"})

    started = time.monotonic()
    result = cli.run("await", "plan", "--timeout", "30")
    assert result.returncode == Exit.OK
    assert "STATUS: approved" in result.stdout
    assert time.monotonic() - started < 10


def test_await_ends_when_a_decision_lands_mid_wait(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")

    waiter = subprocess.Popen(
        [sys.executable, "-m", "mdreview", "await", "plan", "--timeout", "60"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=cli.env,
        cwd=cli.workdir,
    )
    try:
        time.sleep(1.0)
        assert waiter.poll() is None, "await must still be waiting before the decision"
        with cli.api() as client:
            client.post(
                "/api/documents/plan/versions/1/comments",
                json={"line_start": 1, "line_end": 1, "body": "tighten"},
            )
            client.post(
                "/api/documents/plan/versions/1/decision",
                json={"status": "changes_requested"},
            )
        stdout, _ = waiter.communicate(timeout=15)
    finally:
        if waiter.poll() is None:
            waiter.kill()

    assert waiter.returncode == Exit.CHANGES_REQUESTED
    assert "STATUS: changes_requested" in stdout
    assert "tighten" in stdout, "the completed wait must carry the feedback"


def test_await_times_out_with_exit_3(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    result = cli.run("await", "plan", "--timeout", "1")
    assert result.returncode == Exit.PENDING
    assert "No decision has been recorded" in result.stdout


def test_await_reports_an_unreachable_server_as_5(
    settings: Settings, data_dir: Path, tmp_path: Path
) -> None:
    runner = CliRunner(settings, data_dir, tmp_path)
    runner.env["MDREVIEW_AUTOSTART"] = "0"
    result = runner.run("await", "ghost", "--timeout", "3")
    assert result.returncode == Exit.UNREACHABLE


# -- session provenance -----------------------------------------------------

# The suite itself runs inside an agent session, so detection tests must pin
# every variable they depend on; an empty value reads as unset.
NO_SESSION = {
    "MDREVIEW_SESSION_ID": "",
    "OPENCODE_SESSION_ID": "",
    "CLAUDE_CODE_SESSION_ID": "",
    "OPENCODE": "",
    "CLAUDECODE": "",
}


def test_submit_records_the_detected_session(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    claude_id = "1e0e56a0-58bf-483b-b57b-9c5f723dec63"
    env = {**NO_SESSION, "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": claude_id}
    assert cli.run("submit", "PLAN.md", "--no-open", env=env).returncode == Exit.OK

    with cli.api() as client:
        document = client.get("/api/documents/plan")
    assert document["session_tool"] == "claude-code"
    assert document["session_id"] == claude_id


def test_submit_records_the_tool_when_the_id_is_scrubbed(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    env = {**NO_SESSION, "OPENCODE": "1"}
    cli.run("submit", "PLAN.md", "--no-open", env=env)

    with cli.api() as client:
        document = client.get("/api/documents/plan")
    assert document["session_tool"] == "opencode"
    assert document["session_id"] is None


def test_submit_outside_any_session_records_nothing(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open", env=NO_SESSION)

    with cli.api() as client:
        document = client.get("/api/documents/plan")
    assert document["session_tool"] is None
    assert document["session_id"] is None


# -- delete -----------------------------------------------------------------


def test_delete_asks_and_a_decline_changes_nothing(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")

    result = cli.run("delete", "plan", stdin="n\n")
    assert result.returncode == Exit.OK
    assert "cannot be undone" in result.stdout
    assert "nothing deleted" in result.stdout
    assert cli.run("status", "plan").returncode == Exit.OK


def test_delete_confirmed_removes_the_document(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")

    result = cli.run("delete", "plan", stdin="y\n")
    assert result.returncode == Exit.OK
    assert "deleted plan" in result.stdout
    assert cli.run("status", "plan").returncode == Exit.ERROR


def test_delete_yes_skips_the_prompt(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")

    result = cli.run("delete", "plan", "--yes")
    assert result.returncode == Exit.OK
    assert "Permanently delete" not in result.stdout
    assert cli.run("status", "plan").returncode == Exit.ERROR


def test_delete_unknown_slug_fails_clearly(cli: CliRunner) -> None:
    result = cli.run("delete", "ghost", "--yes")
    assert result.returncode == Exit.ERROR
    assert "ghost" in result.stderr


def test_status_prints_one_line(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    result = cli.run("status", "plan")
    assert result.returncode == Exit.OK
    assert result.stdout.strip() == "STATUS: pending   VERSION: 1   OPEN: 0"


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


# -- multi-file submission ---------------------------------------------------


def _write_bundle(cli: CliRunner) -> None:
    (cli.workdir / "change-x" / "specs").mkdir(parents=True, exist_ok=True)
    (cli.workdir / "change-x" / "proposal.md").write_text("## Why\n\nBecause.\n")
    (cli.workdir / "change-x" / "specs" / "spec.md").write_text("## ADDED\n\nA requirement.\n")


def test_submit_several_files_assembles_under_path_headings(cli: CliRunner) -> None:
    _write_bundle(cli)
    result = cli.run(
        "submit", "change-x/proposal.md", "change-x/specs/spec.md", "--no-open"
    )
    assert result.returncode == Exit.OK

    with cli.api() as client:
        content = client.get_text("/api/documents/change-x/versions/1/content")
    assert content == (
        "# change-x/proposal.md\n\n## Why\n\nBecause.\n"
        "\n# change-x/specs/spec.md\n\n## ADDED\n\nA requirement.\n"
    )


def test_resubmitting_the_same_files_reuses_the_round(cli: CliRunner) -> None:
    _write_bundle(cli)
    args = ("submit", "change-x/proposal.md", "change-x/specs/spec.md", "--no-open")
    cli.run(*args)
    # Same slug, same bytes: the pending round is reused, as for one file.
    result = cli.run(*args, "--slug", "change-x")
    assert "reusing existing round" in result.stdout


def test_multi_file_defaults_derive_from_the_common_parent(cli: CliRunner) -> None:
    _write_bundle(cli)
    cli.run("submit", "change-x/proposal.md", "change-x/specs/spec.md", "--no-open")
    result = cli.run("list", "--json")
    item = json.loads(result.stdout)[0]
    assert item["slug"] == "change-x"
    assert item["title"] == "change-x"


def test_single_file_submission_is_unchanged(cli: CliRunner) -> None:
    cli.write("PLAN.md", PLAN)
    cli.run("submit", "PLAN.md", "--no-open")
    with cli.api() as client:
        content = client.get_text("/api/documents/plan/versions/1/content")
    assert content == PLAN  # no heading injected, byte-identical


def test_multi_file_with_a_missing_file_records_nothing(cli: CliRunner) -> None:
    _write_bundle(cli)
    result = cli.run("submit", "change-x/proposal.md", "nope.md", "--no-open")
    assert result.returncode == Exit.ERROR
    assert "nope.md" in result.stderr
    assert json.loads(cli.run("list", "--json").stdout) == []


def test_review_maps_comments_back_to_source_files(cli: CliRunner) -> None:
    _write_bundle(cli)
    cli.run("submit", "change-x/proposal.md", "change-x/specs/spec.md", "--no-open")

    with cli.api() as client:
        # "A requirement." is line 3 of specs/spec.md: assembly lines are
        # proposal (heading L1, content L3-5), spec heading L7, content L9-11.
        client.post(
            "/api/documents/change-x/versions/1/comments",
            json={"line_start": 11, "line_end": 11, "body": "tighten this"},
        )
        client.post(
            "/api/documents/change-x/versions/1/decision",
            json={"status": "changes_requested"},
        )

    result = cli.run("review", "change-x")
    assert result.returncode == Exit.CHANGES_REQUESTED
    assert "(change-x/specs/spec.md:3)" in result.stdout
    assert "same files in the same order" in result.stdout
