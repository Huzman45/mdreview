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
    # 2 — the comment lifecycle shrinks to open/outdated, edits are stamped,
    # and comments become deletable.
    #
    # ``resolved`` is retired: the revision that follows feedback already marks
    # open comments ``outdated``, so a separate reviewer-side "done" state never
    # meant anything distinct. Existing ``resolved`` rows become ``outdated``,
    # which is what they always were — no longer outstanding, kept readable.
    #
    # ``comment_seq`` is the reference allocator, moved off the comment rows
    # precisely because rows can now be deleted: a count (or max) over surviving
    # rows would hand a deleted reference to new feedback. It is allocator
    # state, not domain state, so the Version model does not carry it. Existing
    # versions start at their current highest reference; nothing can have been
    # deleted before this step exists, so that is the true high-water mark.
    #
    # SQLite cannot alter a CHECK constraint in place, so the table is rebuilt:
    # create, copy with the state mapping, drop, rename. The migration runner
    # wraps the whole step in one transaction, and ``comments`` has no children,
    # so the rebuild cannot orphan anything. Dropping the old table drops its
    # index, hence the recreate at the end.
    """
    ALTER TABLE versions ADD COLUMN comment_seq INTEGER NOT NULL DEFAULT 0;

    UPDATE versions SET comment_seq = COALESCE(
        (SELECT MAX(CAST(SUBSTR(ref, 2) AS INTEGER))
           FROM comments WHERE comments.version_id = versions.id),
        0
    );

    CREATE TABLE comments_next (
        id         INTEGER PRIMARY KEY,
        version_id INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
        ref        TEXT    NOT NULL,
        line_start INTEGER NOT NULL,
        line_end   INTEGER NOT NULL,
        quoted     TEXT    NOT NULL,
        body       TEXT    NOT NULL,
        state      TEXT    NOT NULL DEFAULT 'open'
                   CHECK (state IN ('open','outdated')),
        edited_at  TEXT,
        created_at TEXT    NOT NULL,
        UNIQUE (version_id, ref),
        CHECK (line_end >= line_start)
    );

    INSERT INTO comments_next
        (id, version_id, ref, line_start, line_end, quoted, body, state, edited_at, created_at)
    SELECT id, version_id, ref, line_start, line_end, quoted, body,
           CASE state WHEN 'resolved' THEN 'outdated' ELSE state END,
           NULL, created_at
    FROM comments;

    DROP TABLE comments;
    ALTER TABLE comments_next RENAME TO comments;
    CREATE INDEX idx_comments_version ON comments(version_id, state);
    """,
    # 3 — documents can be archived. NULL means active; the timestamp is shown
    # in the archived listing. Nothing to backfill: everything existing is
    # active.
    """
    ALTER TABLE documents ADD COLUMN archived_at TEXT;
    """,
)

SCHEMA_VERSION = len(STEPS)
