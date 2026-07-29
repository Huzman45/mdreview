from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mdreview import db
from mdreview.migrations import SCHEMA_VERSION, STEPS


def test_connect_creates_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deeper" / "db.sqlite"
    conn = db.connect(target)
    conn.close()
    assert target.parent.is_dir()


def test_pragmas_are_applied(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "db.sqlite")
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_migrate_brings_a_fresh_database_to_current(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "db.sqlite")
    assert db.schema_version(conn) == 0
    assert db.migrate(conn) == SCHEMA_VERSION
    assert db.schema_version(conn) == SCHEMA_VERSION
    conn.close()


def test_migrate_creates_the_expected_tables(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "db.sqlite")
    db.migrate(conn)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = {row["name"] for row in rows}
    assert {"documents", "versions", "comments"} <= names
    conn.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    conn = db.connect(path)
    db.migrate(conn)
    conn.execute(
        "INSERT INTO documents (slug, title, created_at) VALUES ('a', 'A', '2026-01-01')"
    )
    conn.close()

    again = db.connect(path)
    assert db.migrate(again) == SCHEMA_VERSION
    # A second run must not recreate tables and lose data.
    assert again.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    again.close()


def test_state_outlives_the_connection(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    with db.session(path) as conn:
        db.migrate(conn)
        conn.execute(
            "INSERT INTO documents (slug, title, created_at) VALUES ('p', 'P', '2026-01-01')"
        )
    with db.session(path) as conn:
        assert conn.execute("SELECT slug FROM documents").fetchone()["slug"] == "p"


def test_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    conn = db.connect(path)
    db.migrate(conn)
    with pytest.raises(RuntimeError), db.transaction(conn):
        conn.execute(
            "INSERT INTO documents (slug, title, created_at) VALUES ('x', 'X', '2026-01-01')"
        )
        raise RuntimeError("boom")
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    conn.close()


def test_migrating_a_schema_1_database_retires_resolved(tmp_path: Path) -> None:
    """A database from before the lifecycle change carries `resolved` rows;
    they become `outdated` — no longer outstanding, kept readable — and
    nothing else about them changes."""
    path = tmp_path / "db.sqlite"
    conn = db.connect(path)
    # Apply only the initial schema, then populate it the way version 1 could.
    conn.executescript(f"BEGIN;\n{STEPS[0]}\nPRAGMA user_version = 1;\nCOMMIT;")
    conn.executescript(
        """
        INSERT INTO documents (id, slug, title, created_at)
            VALUES (1, 'p', 'P', '2026-01-01');
        INSERT INTO versions (id, document_id, n, content, content_sha, status, created_at)
            VALUES (1, 1, 1, '# P', 'sha', 'changes_requested', '2026-01-01');
        INSERT INTO comments
            (version_id, ref, line_start, line_end, quoted, body, state, created_at)
            VALUES (1, 'C1', 1, 1, '# P', 'done already', 'resolved', '2026-01-01'),
                   (1, 'C2', 1, 1, '# P', 'still open', 'open', '2026-01-01'),
                   (1, 'C3', 1, 1, '# P', 'old round', 'outdated', '2026-01-01');
        """
    )
    conn.close()

    conn = db.connect(path)
    assert db.migrate(conn) == SCHEMA_VERSION
    rows = conn.execute(
        "SELECT ref, state, body, edited_at FROM comments ORDER BY ref"
    ).fetchall()
    assert [(r["ref"], r["state"]) for r in rows] == [
        ("C1", "outdated"),
        ("C2", "open"),
        ("C3", "outdated"),
    ]
    assert all(r["edited_at"] is None for r in rows)
    assert rows[0]["body"] == "done already"
    # The reference allocator starts at the existing high-water mark, so the
    # next comment on this version would be C4, not a reused C1.
    assert conn.execute("SELECT comment_seq FROM versions").fetchone()[0] == 3
    # The narrowed constraint is live: `resolved` can no longer be stored.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO comments"
            " (version_id, ref, line_start, line_end, quoted, body, state, created_at)"
            " VALUES (1, 'C4', 1, 1, 'q', 'b', 'resolved', '2026-01-02')"
        )
    conn.close()


def test_review_status_check_constraint_is_enforced(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "db.sqlite")
    db.migrate(conn)
    conn.execute(
        "INSERT INTO documents (id, slug, title, created_at) VALUES (1, 's', 'S', '2026-01-01')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO versions (document_id, n, content, content_sha, status, created_at)"
            " VALUES (1, 1, 'x', 'sha', 'nonsense', '2026-01-01')"
        )
    conn.close()


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "db.sqlite")
    db.migrate(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO versions (document_id, n, content, content_sha, created_at)"
            " VALUES (999, 1, 'x', 'sha', '2026-01-01')"
        )
    conn.close()


def test_connection_survives_use_from_another_thread(tmp_path: Path) -> None:
    """FastAPI tears down sync dependencies in a threadpool, so the closing
    thread is not always the opening thread. sqlite3's same-thread check would
    turn that into an intermittent 500 on an otherwise successful request."""
    from concurrent.futures import ThreadPoolExecutor

    conn = db.connect(tmp_path / "db.sqlite")
    conn.execute("SELECT 1")
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(conn.close).result()
