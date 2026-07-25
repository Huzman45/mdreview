## Context

The repository is empty. Everything here is greenfield, so the design's job is to fix
the handful of decisions that are expensive to reverse — the storage model, the
anchoring strategy, and the agent handshake — and to keep the rest boring.

The operating constraints are unusual enough to be worth restating, because they
justify choices that would be wrong in a normal web service:

- **One user, on loopback, on their own machine.** There is no adversary on the
  network, no tenancy, and no scaling dimension. Authentication, rate limiting, and
  horizontal scale are all absent by design.
- **Two clients with opposite needs.** A human wants rendered prose in a browser. An
  agent wants a terse, unambiguous, machine-branchable answer. The same state has to
  serve both without either being a second-class citizen.
- **The agent cannot be kept waiting.** Architecture decision 4 in the project context
  settles this: the agent submits, stops, and is nudged by the human. This removes the
  hardest part of the problem (holding a connection across a human-scale delay) and its
  entire supporting apparatus.

Decisions 1–8 in the project context are settled inputs to this design, not options.
This document explains how they compose and fills in what they leave open.

## Goals / Non-Goals

**Goals:**

- Comments that can never point at the wrong text, no matter how the document evolves.
- A review page that is pleasant to read, with comment granularity fine enough for
  plan documents — per bullet, not per section.
- An agent handshake in which "not yet reviewed" is impossible to confuse with
  "approved".
- Zero installation ceremony: no daemon, no build step, no Node toolchain.
- A codebase small enough to read in one sitting.

**Non-Goals:**

- Anchor relocation across versions. Explicitly rejected; see decision 2.
- Any blocking or push mechanism — no long-poll, no websockets, no notifications.
- MCP integration. The agent surface is the CLI plus a skill (decision 8).
- Editing documents in the browser. The agent owns the file.
- Everything in the proposal's Non-goals section.

## Decisions

### D1. A review round is a version row, not a separate entity

Following decision 1, review status lives on `versions` rather than in a `reviews`
table. A review round and a version are the same thing: submitting content opens a
round, and recording a decision closes it.

*Alternative considered:* a separate `reviews` table keyed by version. Rejected — it
permits states the domain does not have (two open reviews of one version, a review with
no version) and buys nothing, since the cardinality is strictly one-to-one.

*Consequence:* re-deciding a version is a conflict, not an update. To reopen, submit a
new version. This is why `review-decisions` specifies 409 on a second decision.

### D2. Anchors are safe because their target is frozen

Comments store `(version_id, line_start, line_end)` plus the quoted source text.
Because a version's bytes never change (decision 2), an anchor cannot drift. The entire
class of bugs around comment re-anchoring is designed out rather than solved.

*Alternative considered:* fuzzy re-anchoring by quoted text, as Notion does. Rejected —
it is the single largest source of complexity in tools like this, and its failure mode
(a comment silently attached to the wrong passage) is worse than the failure mode of
the chosen approach (a comment honestly marked `outdated`).

*Consequence:* on a new version, prior `open` comments become `outdated`. The reviewer
re-raises anything still unaddressed. For plan documents, which are revised wholesale
rather than line-tweaked, this matches how review actually proceeds.

Storing the quoted text at creation is what makes `outdated` comments still useful —
they remain readable as history without needing the old version rendered.

### D3. `token.map` provides anchors without a second parse

`markdown-it-py` reports a source line range on every block-level token. Rendering
walks the token stream once and wraps each top-level block in an element carrying
`data-line-start` / `data-line-end`. Verified granularity on a representative document:

```
heading_open      map=[0, 1]
paragraph_open    map=[2, 4]
list_item_open    map=[5, 6]     <- per bullet
list_item_open    map=[6, 8]
fence             map=[8, 11]
```

Headings, individual paragraphs, individual list items, and fenced blocks are each
separately addressable. That is the right granularity for plan review, where feedback
is overwhelmingly "this bullet is wrong".

*Alternative considered:* a raw line-numbered gutter, GitHub-diff style. Rejected as
the primary view — reading raw markdown is the pain being removed. Because anchors are
stored as line ranges rather than block identifiers, a raw view remains addable later
with no schema change and no data migration, which makes this choice cheap to revisit.

*Known limitation:* a single line inside a fenced block, or one sentence inside a
wrapped paragraph, cannot be targeted — those tokens are atomic. Accepted.

### D4. Markdown rendering is untrusted input

Document content originates from an agent and comment bodies from a human, so both are
untrusted. `markdown-it-py` is configured with HTML disabled, so embedded tags are
emitted as text rather than markup. Link targets are filtered against a scheme
allow-list to neutralise `javascript:` URLs. Comment bodies are stored as plain text
and escaped by Jinja2's autoescaping at render time; they are never parsed as markdown.

This is cheap here and awkward to retrofit, which is why it is specified rather than
left to implementation taste.

### D5. Server-rendered Jinja2 with htmx, no build step

The interactions are: open a page, select a block, submit a comment, click a decision.
Each is a form post that swaps a fragment. htmx covers all of it; the only bespoke
JavaScript is block selection and revealing the comment form, on the order of 60 lines.

*Alternative considered:* a React/Vite SPA. Rejected — it introduces a bundler, a
package manager, a build step, and a second language for no interaction that htmx
cannot express. For a single-user localhost tool that is pure carrying cost.

htmx is vendored as a static asset rather than loaded from a CDN, so the tool works
offline.

### D6. Exit codes are the agent-facing contract

The `review` command's exit status is the API. Text output is for the agent's benefit
but is not what it branches on.

| Code | Meaning | Agent action |
| --- | --- | --- |
| 0 | `approved` | Proceed |
| 2 | `changes_requested` | Address comments, resolve, resubmit |
| 3 | `pending` — no decision recorded | Report and wait; do **not** proceed |
| 4 | `cancelled` | Stop and ask |
| 5 | API unreachable | Infrastructure failure, not a review outcome |

Code 3 carries most of the weight. In a hands-off loop the human may nudge the agent
before actually clicking anything, and the dangerous failure is an agent reading
"no changes requested" as approval. A distinct non-zero code for "undecided" makes that
misreading impossible. Code 5 is separated for the same reason: a dead server must not
look like a review verdict.

*Alternative considered:* status in stdout JSON with exit 0 throughout. Rejected —
it makes the safe path depend on the agent parsing correctly, and the unsafe path the
default when it does not.

### D7. Lazy autostart instead of a daemon

Any command needing the API attempts it, and on connection refused spawns a detached
server, waits for `/healthz`, and retries once. No launchd job, no login item.

This is only viable because nothing holds a long-lived connection (decision 4) — a
restart mid-review is invisible to everyone, since all state is in SQLite. Under the
originally-considered blocking design a daemon would have been necessary; removing
blocking removed the daemon too.

*Alternative considered:* a launchd agent with `KeepAlive`. Rejected as unnecessary
setup and one more thing to debug.

### D8. Idempotent submission by content digest

Resubmitting byte-identical content while the current version is still `pending`
returns the existing version instead of creating a duplicate round. Agents retry;
without this, a retried `submit` would silently discard the reviewer's in-progress
comments by superseding the version they were attached to.

Once a version has been *decided*, identical content does create a new version — the
reviewer needs a fresh round to decide again, and the digest match is coincidental
rather than a retry.

### D9. Storage schema

`user_version`-based migrations, applied in order at startup. No Alembic: the DDL is
small, the database is disposable, and a 40-line runner has no failure modes worth
tooling.

```sql
-- step 1
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
```

`CHECK` constraints encode the state machines so an invalid state cannot be persisted
even by a buggy code path. `UNIQUE (version_id, ref)` enforces reference stability at
the storage layer. Timestamps are ISO-8601 UTC strings — SQLite has no date type and
text sorts correctly.

Deliberately absent: an `events` audit table. It was considered for debugging and cut
as speculative; the data it would hold is derivable from what is already stored.

### D10. CLI surface

```
mdreview serve   [--port 7391] [--foreground]
mdreview submit  PATH [--slug S] [--title T] [--no-open] [--json]
mdreview review  SLUG [--json]
mdreview resolve SLUG REF...
mdreview list    [--pending] [--json]
mdreview open    SLUG
mdreview status  SLUG
```

`submit` and `review` are the only two an agent needs; the rest exist so a human is
never forced into the browser. `submit` opens the browser by default, since under a
hands-off loop that removes the last click between the human and the page.

### D11. Layout

```
src/mdreview/
  __init__.py      version
  config.py        paths, port, env overrides
  db.py            connection, WAL/pragmas, migration runner
  migrations.py    ordered DDL steps
  models.py        dataclasses + status enums
  store.py         all SQL; the only module that touches the DB
  render.py        markdown-it wrapper, block anchoring, link filtering
  api.py           FastAPI routers (/api/*)
  web.py           Jinja2 + htmx routes
  server.py        app factory, lifespan, uvicorn entrypoint
  cli.py           Typer app, exit-code mapping, autostart
  client.py        HTTP client used by the CLI
  templates/       Jinja2
  static/          htmx + CSS
tests/
```

`store.py` is the sole holder of SQL, so the schema can be reasoned about in one file
and tests can drive the domain without HTTP. `render.py` is pure — content in, HTML and
block ranges out — which makes the anchoring logic, the part most likely to harbour
bugs, testable without a server or a database.

## Risks / Trade-offs

- **The human forgets to nudge the agent, and the loop stalls silently.** → `submit`
  opens the browser immediately, and the agent's stop message carries the URL, so the
  review is in front of the human the moment it exists. Accepted as inherent to the
  chosen hands-off model; the alternative was blocking, which was rejected.
- **An agent treats exit 3 as success and implements an unapproved plan.** → Distinct
  non-zero code, output that says so in the first line, and an explicit skill
  instruction forbidding it. This is the most damaging failure mode available, hence
  three independent guards.
- **A reviewer's in-progress comments are wiped by an agent retrying `submit`.** →
  D8 makes identical resubmission against a pending version a no-op.
- **Comments marked `outdated` en masse feel like lost work on long documents.** →
  Quoted source is retained so they stay readable as history. If this proves annoying
  in practice, the mitigation is a diff view between versions, not anchor relocation.
- **Two agents submit under the same derived slug and collide.** → Slugs are unique
  and derived slugs get a numeric suffix on collision; `project_path` and `session_id`
  are surfaced so the reviewer can tell submissions apart.
- **`token.map` granularity is coarser than a reviewer wants inside code blocks.** →
  Accepted limitation of D3, cheap to revisit because anchors are line ranges.
- **Port 7391 is already taken.** → Configurable by flag and environment variable;
  autostart failure reports the port and log path rather than hanging.
- **A stale server runs old code after an upgrade.** → `/healthz` reports the app
  version, and the CLI warns when it differs from its own.

## Migration Plan

Nothing to migrate; the project is new. Schema evolution is by appending a step to
`migrations.py`, applied automatically on next start. Rollback for a bad local state is
deleting the database file, which is acceptable for a tool whose contents are
regenerable review history rather than records of value.

Delivery is a Graphite stack, tracer-bullet ordered so the tool runs end to end from
the first implementation PR and every subsequent PR leaves it running.

## Open Questions

None blocking. Two deferred until the tool has been used in anger:

- Whether a version-to-version diff view is worth building, which depends on how often
  `outdated` comments actually cause re-work.
- Whether a raw line-numbered view is needed for code-heavy documents. Deliberately
  cheap to add later; see D3.
