from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mdreview import db
from mdreview.migrations import SCHEMA_VERSION


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
