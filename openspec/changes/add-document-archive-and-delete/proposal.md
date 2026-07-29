## Why

The index accumulates every document ever submitted. Finished reviews, test
runs, and abandoned plans pile up in "Decided" and drown the two documents
that still matter. There is no way to put a document away — short of editing
the database.

The user asked to "delete and/or archive" from the index. These solve
different problems and this change ships both, in different places: archive is
the everyday gesture and lives in the UI; delete is the destructive one and
lives in the CLI, where it can ask twice and is out of reach of a stray tap
on an iPad.

## What Changes

- **Archive from the index.** Each row gains a quiet Archive control; an
  archived document leaves the index (and the pending API listing) but keeps
  its pages readable — it is a decision record, not clutter. A count link at
  the foot of the index leads to an archived listing with Restore.
- **Archiving an undecided document cancels its round.** Putting away a
  document that is waiting for you is a decision — "I am not reviewing this" —
  and the agent reading the outcome gets exit 4 (cancelled, stop and ask)
  instead of polling exit 3 forever.
- **Resubmission reactivates.** A new version of an archived document returns
  it to the index; otherwise an agent's revision would land somewhere the
  reviewer never looks.
- **Delete from the CLI.** `mdreview delete <slug>` removes the document and
  its entire history after an interactive confirmation (`--yes` skips it, for
  scripts). One statement — the schema already cascades — which is exactly why
  it is not a button.

## Capabilities

### New Capabilities

- `document-lifecycle`: archiving, restoring, and deleting whole documents.

### Modified Capabilities

- `review-decisions`: the index and the pending listing cover active documents
  only.
- `document-submission`: a new version reactivates an archived document.

## Non-goals

- **Delete in the browser.** Archive already answers "get this off my index";
  the irreversible operation stays behind a terminal prompt.
- **Bulk operations.** One document at a time; the index is short once
  archiving exists.
- **An agent-facing archive command.** Shelving reviews is the reviewer's
  call; the skill does not mention it.

## Impact

- Migration step 3 (`documents.archived_at`), `models.py`, `store.py`,
  `api.py` (DELETE endpoint), `web.py` (archive/unarchive routes, archived
  page), `cli.py` (`delete`), index template and a small archived listing,
  CSS for the row action.
