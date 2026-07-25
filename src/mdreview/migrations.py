"""Ordered schema migration steps.

Each entry is applied exactly once, in order, and ``PRAGMA user_version`` is set
to the number of steps applied. To evolve the schema, append a step; never edit
one that has shipped.

The ``CHECK`` constraints below encode the review and comment state machines at
the storage layer, so an invalid state cannot be persisted even by a buggy code
path. ``UNIQUE (version_id, ref)`` does the same for comment reference
stability.
"""

from __future__ import annotations

STEPS: tuple[str, ...] = (
    # 1 — initial schema
    """
    CREATE TABLE documents (
        id           INTEGER PRIMARY KEY,
        slug         TEXT    NOT NULL UNIQUE,
        title        TEXT    NOT NULL,
        project_path TEXT,
        session_id   TEXT,
        created_at   TEXT    NOT NULL
    );

    CREATE TABLE versions (
        id            INTEGER PRIMARY KEY,
        document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        n             INTEGER NOT NULL,
        content       TEXT    NOT NULL,
        content_sha   TEXT    NOT NULL,
        status        TEXT    NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','approved','changes_requested','cancelled')),
        decision_note TEXT,
        decided_at    TEXT,
        created_at    TEXT    NOT NULL,
        UNIQUE (document_id, n)
    );

    CREATE TABLE comments (
        id         INTEGER PRIMARY KEY,
        version_id INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
        ref        TEXT    NOT NULL,
        line_start INTEGER NOT NULL,
        line_end   INTEGER NOT NULL,
        quoted     TEXT    NOT NULL,
        body       TEXT    NOT NULL,
        state      TEXT    NOT NULL DEFAULT 'open'
                   CHECK (state IN ('open','resolved','outdated')),
        created_at TEXT    NOT NULL,
        UNIQUE (version_id, ref),
        CHECK (line_end >= line_start)
    );

    CREATE INDEX idx_versions_document ON versions(document_id, n DESC);
    CREATE INDEX idx_comments_version  ON comments(version_id, state);
    """,
)

SCHEMA_VERSION = len(STEPS)
