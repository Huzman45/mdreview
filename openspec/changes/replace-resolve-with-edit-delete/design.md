## Context

The comment lifecycle was designed as `open → resolved | outdated`, with the
agent resolving comments it had addressed. Watching the loop run showed the
resolve step adds no information: the resubmission that follows it outdates
every open comment anyway, and no view ever distinguished `resolved` from
`outdated`. Meanwhile the reviewer has no way to correct their own notes.

## Goals / Non-Goals

**Goals:**

- Two comment states, each with one meaning: `open` = awaiting the agent,
  `outdated` = superseded by a revision.
- Reviewer-controlled edit and delete, with reference stability preserved.
- Migrate existing databases without losing any comment.

**Non-Goals:**

- Any agent-side mutation of comments.
- Re-anchoring or re-quoting on edit.

## Decisions

### D1. `resolved` rows become `outdated`, not deleted

The migration must do something with existing `resolved` rows. Deleting them
would erase feedback the reviewer wrote; keeping a legacy state would defeat
the point. `outdated` is exactly what they are — no longer outstanding, kept
readable against the version they were written on — so the copy step maps
`resolved → outdated`.

SQLite cannot alter a `CHECK` constraint in place, so the step creates the new
table, copies with the state mapping, drops the old one, renames, and recreates
the index — all inside the single transaction the migration runner already
wraps around each step. `comments` has no children, so the rebuild cannot break
a foreign key.

### D2. Edit changes the body and nothing else

A comment's anchor (line range) and quoted source are what make it meaningful
after the fact; letting an edit move them would be re-anchoring by hand, with
the same silent-misattachment failure mode the tool already refuses to
automate. The quote stays valid precisely because the anchor is immutable.
Only the body changes.

An edit is visible: `edited_at` is stamped and the margin shows an "edited"
marker. An agent may have already read the old body; pretending the note was
always its current text would hide that from the reviewer. The report does not
surface it — the agent acts on the current text either way.

### D3. Only open comments can be edited or deleted

An `outdated` comment is the record of a past round; editing history would
falsify it, and deleting it would erase it. The store refuses both. This also
keeps the UI honest: the margin only offers the controls where they can work,
on the latest pending version.

### D4. References come from a counter on the version, not from the rows

`next_ref` counted rows, which reuses a reference the moment one is deleted —
an agent that acted on yesterday's `C2` would see today's unrelated `C2`.
Taking `max + 1` over surviving rows instead is subtly wrong the same way:
delete the *highest* reference and the max drops with it. The allocator has to
live outside the rows it numbers, so each version carries a `comment_seq`
counter, bumped on every allocation and never decremented. It is allocator
state, not domain state — the `Version` model does not expose it. The
`UNIQUE (version_id, ref)` constraint remains the backstop.

### D5. Delete is confirmed, edit is not

Delete destroys the reviewer's own writing, so the margin asks once
(`hx-confirm`). Edit is reversible by editing again; a confirmation there
would be friction with nothing to protect.

### D6. The rename is "open", not a euphemism for resolve

With `resolved` gone, "unresolved" would be a name for a concept that no longer
exists (`not resolved` reads as `open ∪ outdated`, which is wrong). The state
field, report header, and index chip all say **open**: `open_comments` in the
state JSON, `OPEN: n` in the report header, "n open" on the index. The agent
skill and specs change in the same commit, so the documented contract and the
implemented one cannot drift.

## Risks / Trade-offs

- **Breaking the agent contract.** Any agent following the old skill will run
  `mdreview resolve` and fail. Mitigated: the CLI removal, skill rewrite, and
  spec change land atomically, and the failure is loud (unknown command) rather
  than silent. The one live consumer of this contract is the operator's own
  agents, which read the skill fresh each session.
- **`edited_at` is the only schema addition.** Storing edit history (old
  bodies) was considered and rejected: single reviewer, local tool — the
  marker is enough.

## Migration

Step 2 in `migrations.py`; applied automatically on next server start. Not
reversible (the `resolved`/`outdated` distinction is collapsed), which is
acceptable because nothing distinguished them before either.
