"""The capability token that guards LAN access.

Binding to the LAN is what makes the service reachable from another machine;
this token is what makes it usable. Loopback is never asked for it, so the agent
CLI — which issues many requests per review — is unaffected.

The token defends against other machines on a shared network casually reaching
the port. It is **not** protection against someone able to read packets on the
wire: traffic is plaintext HTTP by design.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from . import config

#: 256 bits, comfortably above the 128-bit floor the specification requires.
TOKEN_BYTES = 32

COOKIE_NAME = "mdreview_token"
QUERY_PARAM = "t"


def token_path() -> Path:
    return config.data_dir() / "lan_token"


def read() -> str | None:
    path = token_path()
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def ensure() -> str:
    """Return the current token, creating one on first LAN use.

    Generated lazily rather than at install time, so a loopback-only user never
    has a credential sitting on disk. Stable across restarts, because a token
    that changed on every start would invalidate the phone's cookie constantly.
    """
    existing = read()
    if existing:
        return existing

    value = secrets.token_urlsafe(TOKEN_BYTES)
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create with owner-only permissions from the outset rather than chmod-ing
    # afterwards, which would leave a window where it is world-readable.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(value)
    return value


def rotate() -> str:
    """Discard the current token and mint a new one."""
    token_path().unlink(missing_ok=True)
    return ensure()


def matches(candidate: str | None) -> bool:
    """Constant-time comparison against the current token."""
    if not candidate:
        return False
    current = read()
    if not current:
        return False
    return secrets.compare_digest(candidate, current)
