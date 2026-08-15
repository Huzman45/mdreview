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
ENV_ALLOW_LAN = "MDREVIEW_ALLOW_LAN"
ENV_WEBHOOK_URL = "MDREVIEW_WEBHOOK_URL"
ENV_WEBHOOK_TOKEN = "MDREVIEW_WEBHOOK_TOKEN"


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


def allow_lan_enabled() -> bool:
    """Whether an unauthenticated private-LAN bind was explicitly allowed."""
    return os.environ.get(ENV_ALLOW_LAN, "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def default_webhook_url() -> str | None:
    """Where a recorded decision is announced, if anywhere.

    Unset is the ordinary case: the review loop is complete without a listener.
    """
    return os.environ.get(ENV_WEBHOOK_URL, "").strip() or None


def default_webhook_token() -> str | None:
    """The bearer token presented to the webhook receiver, if it wants one.

    A receiver that acts on a decision has its own reasons to authenticate its
    callers, and a URL alone cannot carry an `Authorization` header.
    """
    return os.environ.get(ENV_WEBHOOK_TOKEN, "").strip() or None


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


def require_safe_bind(host: str, *, allow_lan: bool = False) -> str:
    """Accept loopback, or one explicit private address with an opt-in.

    Wildcard addresses remain forbidden even with the opt-in: binding to one
    concrete interface is enough for phone access without also exposing the
    service on Wi-Fi, VPN, and every future interface.
    """
    if is_loopback(host):
        return host
    if not allow_lan:
        raise ValueError(
            f"refusing to bind to {host!r}: mdreview has no authentication; "
            f"pass --allow-lan to expose it on a private network"
        )
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError(
            "LAN binding requires a concrete private IP address, not a hostname"
        ) from exc
    if address.is_unspecified:
        raise ValueError(f"refusing wildcard address {host!r}; choose one private LAN address")
    if not address.is_private:
        raise ValueError(
            f"refusing non-private address {host!r}; --allow-lan only permits "
            f"private network addresses"
        )
    return host


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    database: Path
    allow_lan: bool = False
    webhook_url: str | None = None
    webhook_token: str | None = None

    @classmethod
    def load(
        cls,
        *,
        host: str | None = None,
        port: int | None = None,
        database: Path | None = None,
        allow_lan: bool = False,
        webhook_url: str | None = None,
        webhook_token: str | None = None,
    ) -> Settings:
        allow_lan = allow_lan or allow_lan_enabled()
        return cls(
            host=require_safe_bind(
                host if host is not None else default_host(), allow_lan=allow_lan
            ),
            port=port if port is not None else default_port(),
            database=database if database is not None else db_path(),
            allow_lan=allow_lan,
            webhook_url=webhook_url if webhook_url is not None else default_webhook_url(),
            webhook_token=(
                webhook_token if webhook_token is not None else default_webhook_token()
            ),
        )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
