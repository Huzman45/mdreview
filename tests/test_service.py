"""The service definition is generated, so what it contains is asserted directly.

The critical property is that it supervises this tool and nothing else. A launchd
job that acts on another application is how you end up repeatedly killing the
operator's editor.
"""

from __future__ import annotations

import plistlib

from mdreview import service


def test_the_job_runs_only_this_tools_wrapper() -> None:
    job = service.render_plist(
        wrapper="/Users/x/.local/bin/mdreview-lan-server",
        out_log="/tmp/o.log",
        err_log="/tmp/e.log",
    )
    assert job["ProgramArguments"] == [
        "/bin/zsh",
        "/Users/x/.local/bin/mdreview-lan-server",
    ]


def test_the_job_names_no_other_application() -> None:
    job = service.render_plist(wrapper="/w", out_log="/o", err_log="/e")
    blob = plistlib.dumps(job).decode()
    for foreign in ("OpenCode", "osascript", "pkill", "kill", "Electron", "launchctl"):
        assert foreign not in blob, foreign


def test_the_job_survives_logout_and_crashes() -> None:
    job = service.render_plist(wrapper="/w", out_log="/o", err_log="/e")
    assert job["RunAtLoad"] is True
    assert job["KeepAlive"] is True


def test_the_job_logs_somewhere_readable() -> None:
    job = service.render_plist(wrapper="/w", out_log="/logs/out", err_log="/logs/err")
    assert job["StandardOutPath"] == "/logs/out"
    assert job["StandardErrorPath"] == "/logs/err"


def test_the_job_is_serialisable_as_a_plist() -> None:
    job = service.render_plist(wrapper="/w", out_log="/o", err_log="/e")
    assert plistlib.loads(plistlib.dumps(job))["Label"] == service.LABEL


# -- the wrapper ------------------------------------------------------------


def test_the_wrapper_resolves_the_address_rather_than_hardcoding_it() -> None:
    """Baking the address in at install time would break on a DHCP change."""
    script = service.render_wrapper(mdreview="/usr/local/bin/mdreview", port=7391)
    assert "lan-address" in script
    assert '--host "$host"' in script


def test_the_wrapper_passes_the_lan_opt_in() -> None:
    script = service.render_wrapper(mdreview="/m", port=7391)
    assert "--allow-lan" in script
    assert "--foreground" in script


def test_the_wrapper_uses_the_configured_port() -> None:
    assert "--port 7654" in service.render_wrapper(mdreview="/m", port=7654)


def test_the_wrapper_fails_loudly_with_no_address() -> None:
    script = service.render_wrapper(mdreview="/m", port=7391)
    assert "not starting" in script
    assert "exit 1" in script


def test_the_wrapper_refers_only_to_this_tool() -> None:
    script = service.render_wrapper(mdreview="/usr/local/bin/mdreview", port=7391)
    for foreign in ("OpenCode", "osascript", "pkill", "open -a"):
        assert foreign not in script, foreign


# -- paths and state --------------------------------------------------------


def test_paths_are_under_the_users_own_directories() -> None:
    assert service.plist_path().name == f"{service.LABEL}.plist"
    assert "LaunchAgents" in str(service.plist_path())
    assert service.log_dir().name == "mdreview"


def test_the_label_is_specific_to_this_tool() -> None:
    """It must not collide with any other agent on the machine."""
    assert service.LABEL == "ai.mdreview.server"
    assert "opencode" not in service.LABEL


def test_state_reports_not_installed_when_no_plist(monkeypatch) -> None:
    from pathlib import Path

    monkeypatch.setattr(service, "plist_path", lambda: Path("/nonexistent/x.plist"))
    result = service.state()
    assert result.installed is False
    assert result.running is False
    assert result.describe() == "not installed"


def test_describe_covers_each_state() -> None:
    assert "not installed" in service.State(False, False, None, None).describe()
    assert "not running" in service.State(True, False, None, None).describe()
    running = service.State(True, True, 123, "10.31.41.9")
    assert "10.31.41.9" in running.describe()
    assert "123" in running.describe()


def test_status_degrades_rather_than_raising_without_lsof(monkeypatch) -> None:
    """A status command must never crash; lsof lives in /usr/sbin and a trimmed
    PATH would otherwise raise FileNotFoundError."""
    monkeypatch.setattr(service.shutil, "which", lambda _: None)
    monkeypatch.setattr(service.Path, "exists", lambda _: False)
    assert service._listening_address(1, 7391) is None
