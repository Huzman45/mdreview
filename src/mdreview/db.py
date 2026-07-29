"""SQLite connection handling and the migration runner.

Connections are created per unit of work rather than shared. SQLite connections
are not safe to use concurrently across threads, and opening one is cheap enough
that pooling would be a premature optimisation for a single-user tool. WAL mode
keeps concurrent readers from blocking the writer.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .migrations import STEPS


def connect(path: Path) -> sqlite3.Connection:
    """Open a connection with the pragmas this application depends on."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread is off because FastAPI runs sync dependencies in a
    # threadpool: the thread that finalises a request's connection is not
    # always the thread that opened it. Each connection still serves one
    # request at a time, so there is no concurrent cross-thread use.
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> int:
    """Apply outstanding migration steps in order. Returns the resulting version.

    Steps already reflected in ``user_version`` are skipped, so this is safe to
    call on every startup.
    """
    current = schema_version(conn)
    for index, step in enumerate(STEPS, start=1):
        if index <= current:
            continue
        # executescript() implicitly commits any open transaction before it runs,
        # so transaction control has to live inside the script rather than around
        # it. Bumping user_version in the same transaction as the DDL keeps a
        # failed migration from being recorded as applied.
        # PRAGMA does not accept bound parameters; index is a trusted integer.
        script = f"BEGIN;\n{step}\nPRAGMA user_version = {index};\nCOMMIT;"
        try:
            conn.executescript(script)
        except Exception:
            conn.executescript("ROLLBACK;")
            raise
    return schema_version(conn)


@contextmanager
def session(path: Path) -> Iterator[sqlite3.Connection]:
    """A connection scoped to one unit of work."""
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Wrap a group of writes so they commit together or not at all."""
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
