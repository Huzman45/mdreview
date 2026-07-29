"""Detecting the agent session a command is running inside.

Both agent tools pass environment down to the shell commands they run, which
is the only signal that names the session that actually issued this command —
process-tree inspection and newest-session heuristics are ambiguous the
moment two sessions share a working directory.

Verified against Claude Code 2.1.220 and opencode 1.18.5:

- Claude Code exports ``CLAUDECODE=1`` and ``CLAUDE_CODE_SESSION_ID`` (a
  UUID) to every shell child. Some spawn paths scrub the id while keeping the
  marker, so a missing id means "unknown", never "not Claude Code".
- opencode exports ``OPENCODE=1`` but no session id; the bundled
  ``contrib/opencode`` plugin injects ``OPENCODE_SESSION_ID`` (``ses_`` + 26
  chars) per command through opencode's ``shell.env`` hook.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

CLAUDE_CODE = "claude-code"
OPENCODE = "opencode"

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_OPENCODE_ID = re.compile(r"^ses_[0-9a-zA-Z]{26}$")


@dataclass(frozen=True, slots=True)
class SessionInfo:
    tool: str | None
    session_id: str | None


def tool_for(session_id: str) -> str | None:
    """The tool a bare identifier belongs to, from its distinctive shape."""
    if _OPENCODE_ID.match(session_id):
        return OPENCODE
    if _UUID.match(session_id):
        return CLAUDE_CODE
    return None


def detect(environ: Mapping[str, str]) -> SessionInfo:
    """Identify the session that ran this command.

    Precedence: an explicit override always wins; then the opencode id,
    which the plugin injects per command and therefore names the proximate
    session; then the Claude Code id, which is inherited through arbitrary
    descendants (an opencode session started inside a Claude Code shell
    carries both — the opencode one issued the command); finally the bare
    presence markers, which give tool-only provenance when ids were scrubbed
    or the plugin is absent.
    """
    explicit = (environ.get("MDREVIEW_SESSION_ID") or "").strip()
    if explicit:
        return SessionInfo(tool=tool_for(explicit), session_id=explicit)

    opencode_id = (environ.get("OPENCODE_SESSION_ID") or "").strip()
    if opencode_id:
        return SessionInfo(tool=OPENCODE, session_id=opencode_id)

    claude_id = (environ.get("CLAUDE_CODE_SESSION_ID") or "").strip()
    if claude_id:
        return SessionInfo(tool=CLAUDE_CODE, session_id=claude_id)

    if environ.get("OPENCODE"):
        return SessionInfo(tool=OPENCODE, session_id=None)
    if environ.get("CLAUDECODE"):
        return SessionInfo(tool=CLAUDE_CODE, session_id=None)
    return SessionInfo(tool=None, session_id=None)
