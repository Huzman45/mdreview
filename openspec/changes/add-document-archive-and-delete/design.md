## Context

Documents are never removed. `documents` already cascades to `versions` and
`comments`, so deletion is mechanically trivial and semantically dangerous —
the combination that wants a confirmation step. Archive has no storage support
at all.

## Goals / Non-Goals

**Goals:** put documents away from the browser; destroy them only from the
terminal; never leave an agent polling a review nobody will do.

**Non-Goals:** trash-with-retention semantics; multi-select; agent-driven
archiving.

## Decisions

### D1. Archive in the UI, delete in the CLI

A review tool's history is a record of decisions; a record you can no longer
read is worse than a cluttered list, so the browser — used from an iPad, where
taps go astray — gets the reversible operation only. Delete exists for what
archive cannot do (test documents, accidental submissions, genuinely dead
work) and lives in the CLI, where "are you sure" is a real prompt
(`--yes` for scripts) and the blast radius is stated: the document, all its
versions, all their comments.

### D2. `archived_at` timestamp, not a boolean

A nullable timestamp costs the same as a flag and answers "when was this put
away", which the archived listing shows. Active means `archived_at IS NULL`.

### D3. Archiving an undecided document cancels the open round

Leaving the round `pending` would mean an agent loyally following the skill
polls exit 3 — "still outstanding, do not proceed" — for a review that will
never happen. Cancelling is honest: exit 4 tells it to stop and ask. The
transition happens inside the archive transaction, with a decision note saying
the document was archived without review. Decided rounds are untouched —
archiving a decided document is pure shelving.

### D4. Resubmission reactivates

`submit` clears `archived_at` on an existing document. The agent resubmitting
a revision believes it is opening a review round; if the document stayed
archived, the round would be invisible. Reactivation puts it back under
"Waiting for you", which is where a new pending version belongs. An archived
document's slug therefore stays reserved — archive is shelving, not freeing
the name; delete is how a name is truly released.

### D5. The index row becomes a wrapper so the action is not inside the link

Each row is currently one `<a>`. A button inside an anchor is invalid and
mis-clickable, so the row becomes a wrapper holding the link and a plain form
button. The archive form posts and redirects (303, back to the referring
list); no htmx, because the whole list changes anyway and a full GET is the
simplest thing that is correct on every device.

### D6. Archived documents stay readable, and stay out of the way

Pages under `/d/{slug}` keep working — the record survives. The index, the
pending API filter, and `mdreview list --pending` cover active documents only;
the full API listing gains an `archived` filter instead of hiding the state.
The archived listing is its own quiet page (`/archived`), reachable from a
count at the foot of the index only when there is something in it.

## Risks / Trade-offs

- **A stray tap can still archive.** Acceptable: one tap on Restore undoes
  it, and nothing is lost in between.
- **Cancelling on archive writes a decision the reviewer did not click.** The
  note on the version says the archive did it; the alternative (eternal
  pending) misleads the agent, which is worse than surprising the reviewer.

## Migration

Step 3: `ALTER TABLE documents ADD COLUMN archived_at TEXT`. Nothing to
backfill; every existing document is active.
