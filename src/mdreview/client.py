"""HTTP client used by the CLI, with lazy server autostart.

There is no daemon, so every command that needs the API is responsible for
making it available. This is only safe because nothing ever holds a long-lived
connection: all state lives in SQLite, so a server that starts, stops, or
restarts between commands is invisible to the user.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Any

import httpx

from . import config
from .config import Settings


class ApiUnreachable(RuntimeError):
    """The API is not running and could not be started."""


class ApiError(RuntimeError):
    """The API responded with an error status."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class Client:
    def __init__(self, settings: Settings, *, autostart: bool | None = None) -> None:
        self._settings = settings
        self._autostart = config.autostart_enabled() if autostart is None else autostart
        # This client only talks to an explicitly selected local interface.
        # Honouring HTTP(S)_PROXY here sends private-LAN readiness checks through
        # a corporate proxy, where they time out even though the server is up.
        self._http = httpx.Client(base_url=settings.base_url, timeout=10.0, trust_env=False)

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # -- server lifecycle ---------------------------------------------------

    def is_up(self) -> bool:
        try:
            response = self._http.get("/healthz", timeout=1.0)
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def server_version(self) -> str | None:
        try:
            response = self._http.get("/healthz", timeout=1.0)
            return str(response.json().get("version"))
        except (httpx.HTTPError, ValueError):
            return None

    def _spawn(self) -> None:
        log = config.log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        handle = log.open("a")
        command = [
            sys.executable,
            "-m",
            "mdreview",
            "serve",
            "--host",
            self._settings.host,
            "--port",
            str(self._settings.port),
            "--foreground",
        ]
        if self._settings.allow_lan:
            command.append("--allow-lan")
        subprocess.Popen(
            command,
            stdout=handle,
            stderr=handle,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    def ensure_up(self, *, timeout: float = 15.0) -> None:
        """Start a server if none is reachable, and wait until it answers."""
        if self.is_up():
            return
        if not self._autostart:
            raise ApiUnreachable(
                f"no server reachable at {self._settings.base_url} and autostart is disabled"
            )
        self._spawn()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_up():
                return
            time.sleep(0.15)
        raise ApiUnreachable(
            f"started a server for {self._settings.base_url} but it did not become "
            f"ready within {timeout:.0f}s; see {config.log_path()}"
        )

    # -- requests -----------------------------------------------------------

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.ensure_up()
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ApiUnreachable(f"request to {path} failed: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(response.status_code, _detail(response))
        if not response.content:
            return None
        return response.json()

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def get_text(self, path: str, **kwargs: Any) -> str:
        """GET a plain-text resource verbatim; the JSON decode would mangle it."""
        self.ensure_up()
        try:
            response = self._http.get(path, **kwargs)
        except httpx.HTTPError as exc:
            raise ApiUnreachable(f"request to {path} failed: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(response.status_code, _detail(response))
        return response.text

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return str(payload)
