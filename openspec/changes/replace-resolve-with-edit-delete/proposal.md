## Why

Resolve never fit this tool. It was borrowed from multi-party code review, where
the author marks a thread addressed and the reviewer audits that claim later.
Here there is exactly one human, and the agent's revision — not a checkbox — is
what closes feedback out: resubmitting already marks every open comment
`outdated`. In practice `resolved` was a third state that meant nothing distinct,
an extra CLI step (`mdreview resolve`) the agent performed as busywork, and a
button in the margin whose effect the reviewer could neither see nor undo.

What the reviewer actually needs and does not have is control over their own
notes: fixing a typo in a comment, or removing one written against the wrong
block, currently requires poking the database.

## What Changes

- The `resolved` comment state is removed. A comment is either `open` (awaiting
  the agent) or `outdated` (superseded by a revision). Existing `resolved` rows
  migrate to `outdated`, which is what they already meant: no longer
  outstanding, kept for the record.
- The reviewer can **edit** an open comment's body from the margin. The anchor
  and the quoted source are immutable — the note points where it pointed — and
  an edited comment is marked as edited.
- The reviewer can **delete** an open comment from the margin, behind a
  confirmation. Its reference is never reused: a later comment on the same
  version continues the numbering rather than filling the gap, so `C2` can
  never silently mean two different things to an agent.
- `mdreview resolve`, the `/resolve` API endpoint, and the margin's Resolve
  button are removed. The agent loop becomes: read comments, revise the file,
  resubmit — one step shorter than before.
- The concept previously called "unresolved" is renamed **open** everywhere it
  surfaces: the state API field, the report header, and the index chip.

## Capabilities

### Modified Capabilities

- `block-comments`: lifecycle shrinks to `open`/`outdated`; edit and delete are
  added; reference stability now explicitly covers deletion.
- `agent-cli`: the `resolve` command is removed; the report vocabulary changes
  from "unresolved" to "open".
- `agent-skill`: the revision flow no longer includes a resolve step.
- `review-decisions`: the state answer's comment list is described as "open"
  rather than "unresolved".

## Non-goals

- **Editing or deleting from the CLI.** Comments belong to the reviewer; the
  agent reads them and has no business changing them. Both operations are
  browser-only.
- **Comment threads or replies.** The agent's reply is a new version.
- **Touching `outdated`.** Superseding on resubmission is untouched; it is how
  anchoring stays honest and it is load-bearing for edit (an outdated comment
  is history, so it can be neither edited nor deleted).

## Impact

- Schema: one migration step rebuilds `comments` with the narrower `CHECK` and
  an `edited_at` column (SQLite cannot alter a constraint in place).
- `store.py`, `api.py`, `web.py`, `cli.py`, `report.py`, `models.py`, the
  margin template, the index template, and the skill.
- Agent-facing contract: `mdreview resolve` disappears; the state JSON field
  `unresolved` becomes `open_comments`; report labels change. The skill and
  specs move in the same change, so nothing documents the removed command.
