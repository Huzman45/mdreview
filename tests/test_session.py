"""Detecting which agent session a submission came from."""

from __future__ import annotations

from pathlib import Path

from mdreview import db, session
from mdreview.migrations import SCHEMA_VERSION, STEPS

CLAUDE_ID = "1e0e56a0-58bf-483b-b57b-9c5f723dec63"
OPENCODE_ID = "ses_06782d947ffeffTNPErXOMiTGj"


# -- detection --------------------------------------------------------------


def test_nothing_detected_outside_a_session() -> None:
    assert session.detect({}) == session.SessionInfo(tool=None, session_id=None)


def test_claude_code_exports_its_id() -> None:
    info = session.detect({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": CLAUDE_ID})
    assert info == session.SessionInfo(tool="claude-code", session_id=CLAUDE_ID)


def test_opencode_id_comes_from_the_plugin() -> None:
    info = session.detect({"OPENCODE": "1", "OPENCODE_SESSION_ID": OPENCODE_ID})
    assert info == session.SessionInfo(tool="opencode", session_id=OPENCODE_ID)


def test_explicit_override_beats_everything() -> None:
    info = session.detect(
        {
            "MDREVIEW_SESSION_ID": OPENCODE_ID,
            "CLAUDE_CODE_SESSION_ID": CLAUDE_ID,
            "OPENCODE_SESSION_ID": "ses_x",
        }
    )
    assert info.session_id == OPENCODE_ID
    assert info.tool == "opencode"  # inferred from the id's shape


def test_the_proximate_session_wins_when_nested() -> None:
    """An opencode session started inside a Claude Code shell carries both
    ids; the opencode one issued the command."""
    info = session.detect(
        {
            "CLAUDECODE": "1",
            "CLAUDE_CODE_SESSION_ID": CLAUDE_ID,
            "OPENCODE": "1",
            "OPENCODE_SESSION_ID": OPENCODE_ID,
        }
    )
    assert info == session.SessionInfo(tool="opencode", session_id=OPENCODE_ID)


def test_a_scrubbed_id_still_records_the_tool() -> None:
    assert session.detect({"CLAUDECODE": "1"}) == session.SessionInfo(
        tool="claude-code", session_id=None
    )
    assert session.detect({"OPENCODE": "1"}) == session.SessionInfo(
        tool="opencode", session_id=None
    )


def test_tool_inference_from_id_shapes() -> None:
    assert session.tool_for(CLAUDE_ID) == "claude-code"
    assert session.tool_for(OPENCODE_ID) == "opencode"
    assert session.tool_for("something-else") is None


# -- migration backfill -----------------------------------------------------


def test_migration_backfills_the_tool_from_stored_ids(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    conn = db.connect(path)
    # A database as it stood before this change: steps 1-3 applied.
    for index, step in enumerate(STEPS[:3], start=1):
        conn.executescript(f"BEGIN;\n{step}\nPRAGMA user_version = {index};\nCOMMIT;")
    conn.executescript(
        f"""
        INSERT INTO documents (id, slug, title, session_id, created_at) VALUES
            (1, 'claude-doc', 'A', '{CLAUDE_ID}', '2026-01-01'),
            (2, 'oc-doc', 'B', '{OPENCODE_ID}', '2026-01-01'),
            (3, 'bare-doc', 'C', NULL, '2026-01-01'),
            (4, 'odd-doc', 'D', 'not-a-known-shape', '2026-01-01');
        """
    )
    conn.close()

    conn = db.connect(path)
    assert db.migrate(conn) == SCHEMA_VERSION
    rows = dict(conn.execute("SELECT slug, session_tool FROM documents").fetchall())
    assert rows == {
        "claude-doc": "claude-code",
        "oc-doc": "opencode",
        "bare-doc": None,
        "odd-doc": None,
    }
    conn.close()
