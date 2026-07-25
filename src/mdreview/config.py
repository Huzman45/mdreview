"""Runtime configuration: filesystem paths and network binding.

Every value is overridable by environment variable so that tests, and the
occasional port clash, do not require code changes.
"""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PORT = 7391
DEFAULT_HOST = "127.0.0.1"

ENV_HOST = "MDREVIEW_HOST"
ENV_PORT = "MDREVIEW_PORT"
ENV_DATA_DIR = "MDREVIEW_DATA_DIR"
ENV_AUTOSTART = "MDREVIEW_AUTOSTART"


def data_dir() -> Path:
    """Directory holding all local state.

    Honours ``MDREVIEW_DATA_DIR`` first, then ``XDG_DATA_HOME``, and finally
    falls back to the XDG default of ``~/.local/share``.
    """
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "mdreview"


def db_path() -> Path:
    return data_dir() / "db.sqlite"


def log_path() -> Path:
    return data_dir() / "server.log"


def pid_path() -> Path:
    return data_dir() / "server.pid"


def default_port() -> int:
    raw = os.environ.get(ENV_PORT)
    if not raw:
        return DEFAULT_PORT
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{ENV_PORT} must be an integer, got {raw!r}") from exc


def default_host() -> str:
    return os.environ.get(ENV_HOST, DEFAULT_HOST)


def autostart_enabled() -> bool:
    """Whether a command may start a server for itself.

    Disabling this is useful in scripted contexts that would rather fail
    loudly than have a background process appear.
    """
    return os.environ.get(ENV_AUTOSTART, "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def is_loopback(host: str) -> bool:
    """True if ``host`` can only be reached from this machine.

    The service has no authentication of any kind, so binding it anywhere
    reachable from the network would expose read and write access to every
    document to anyone who can route to the port.
    """
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_loopback(host: str) -> str:
    if not is_loopback(host):
        raise ValueError(
            f"refusing to bind to {host!r}: mdreview has no authentication and "
            f"must only listen on a loopback address"
        )
    return host


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    database: Path

    @classmethod
    def load(
        cls,
        *,
        host: str | None = None,
        port: int | None = None,
        database: Path | None = None,
    ) -> Settings:
        return cls(
            host=require_loopback(host if host is not None else default_host()),
            port=port if port is not None else default_port(),
            database=database if database is not None else db_path(),
        )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
