"""Running the review server as a supervised background service (macOS).

The service definition names exactly one program: this tool's own launcher. It
does not quit, restart, or signal any other application, and nothing here should
ever be extended to.

Note on ``KeepAlive``: it is correct for supervising a long-running server, which
is what this is. It is emphatically wrong for supervising a script that exits by
design — launchd restarts such a job forever. That distinction is the difference
between a service and a restart loop.
"""

from __future__ import annotations

import plistlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import config

LABEL = "ai.mdreview.server"


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def wrapper_path() -> Path:
    return Path.home() / ".local" / "bin" / "mdreview-lan-server"


def log_dir() -> Path:
    return Path.home() / "Library" / "Logs" / "mdreview"


def domain() -> str:
    import os

    return f"gui/{os.getuid()}"


def service_target() -> str:
    return f"{domain()}/{LABEL}"


WRAPPER_TEMPLATE = """#!/bin/zsh
# Launched by the {label} LaunchAgent. Do not edit; regenerate with
# `mise run install-service`.
#
# The address is resolved here, at every start, rather than baked in at install
# time, so a changed DHCP lease is picked up by restarting the service.
set -euo pipefail

MDREVIEW={mdreview}

host=$("$MDREVIEW" lan-address) || {{
  echo "no private LAN address available; not starting" >&2
  exit 1
}}

echo "resolved LAN address: $host"
exec "$MDREVIEW" serve --host "$host" --port {port} --allow-lan --foreground
"""


def render_wrapper(*, mdreview: str, port: int) -> str:
    return WRAPPER_TEMPLATE.format(label=LABEL, mdreview=mdreview, port=port)


def render_plist(*, wrapper: str, out_log: str, err_log: str) -> dict[str, object]:
    """The launchd job. Deliberately minimal: one program, nothing else."""
    return {
        "Label": LABEL,
        "ProgramArguments": ["/bin/zsh", wrapper],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": out_log,
        "StandardErrorPath": err_log,
        "ProcessType": "Background",
    }


@dataclass(frozen=True, slots=True)
class State:
    installed: bool
    running: bool
    pid: int | None
    address: str | None

    def describe(self) -> str:
        if not self.installed:
            return "not installed"
        if not self.running:
            return "installed but not running (see logs)"
        where = f" on {self.address}" if self.address else ""
        return f"running{where} (pid {self.pid})"


def _launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=20)


def install(*, mdreview: str, port: int | None = None) -> Path:
    """Write the wrapper and job, then load it."""
    port = port or config.default_port()

    logs = log_dir()
    logs.mkdir(parents=True, exist_ok=True)

    wrapper = wrapper_path()
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(render_wrapper(mdreview=mdreview, port=port), encoding="utf-8")
    wrapper.chmod(0o755)

    target = plist_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        plistlib.dump(
            render_plist(
                wrapper=str(wrapper),
                out_log=str(logs / "server.out.log"),
                err_log=str(logs / "server.err.log"),
            ),
            handle,
        )

    # Replace any previous incarnation rather than stacking on it.
    _launchctl("bootout", service_target())
    _launchctl("bootstrap", domain(), str(target))
    _launchctl("enable", service_target())
    _launchctl("kickstart", service_target())
    return target


def uninstall() -> bool:
    """Stop the service and delete its definition. Safe when nothing is installed."""
    existed = plist_path().exists()
    _launchctl("bootout", service_target())
    plist_path().unlink(missing_ok=True)
    wrapper_path().unlink(missing_ok=True)
    return existed


def state(*, port: int | None = None) -> State:
    """Read the service state from launchd rather than a pidfile.

    A pidfile is a second source of truth that can disagree with reality after a
    crash.
    """
    if not plist_path().exists():
        return State(installed=False, running=False, pid=None, address=None)

    printed = _launchctl("print", service_target()).stdout
    pid: int | None = None
    for line in printed.splitlines():
        stripped = line.strip()
        if stripped.startswith("pid = "):
            try:
                pid = int(stripped.split("=", 1)[1].strip())
            except ValueError:
                pid = None
            break

    address = None
    if pid is not None:
        address = _listening_address(pid, port or config.default_port())

    return State(installed=True, running=pid is not None, pid=pid, address=address)


def _listening_address(pid: int, port: int) -> str | None:
    result = subprocess.run(
        ["lsof", "-nP", "-a", "-p", str(pid), f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in result.stdout.splitlines():
        if "LISTEN" in line and ":" in line:
            for field in line.split():
                if field.endswith(f":{port}"):
                    return field.rsplit(":", 1)[0]
    return None
