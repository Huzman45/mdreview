---
name: md-review
description: Publish a plan, design, or proposal document for the user to review in a browser, then read their decision and line-level comments back. Use whenever you have written a plan the user should approve before you implement it, or when they ask you to "put this up for review", "let me review that", or "send it to mdreview". Also use on resume, when the user says the review is done, to pick up their decision.
license: MIT
compatibility: Requires the mdreview CLI on PATH.
metadata:
  author: fjvillamarin
  version: "2.2"
---

# Reviewing a document with mdreview

`mdreview` turns a markdown file into a web page where the user can comment on
individual blocks — or individual lines — and either approve it or send it back.
You submit, you stop, they review, they nudge you, you read the outcome.

**You never block waiting for the review.** Submit, tell the user the URL, and
end your turn.

## Submitting

Write the document to a file first, then:

```bash
mdreview submit PLAN.md
```

This prints the review URL, opens it in the user's browser, and returns
immediately. Then:

1. If your harness can run background tasks, start the watcher (see below).
2. Tell the user the URL and that you are waiting on their review.
3. **Stop.** Do not start implementing. Do not ask follow-up questions that
   presume approval.

## Waiting hands-free

If — and only if — your harness supports background tasks (processes that
run detached from your turn and notify you when they finish), start one
right after submitting:

```bash
mdreview await <slug>   # run this AS A BACKGROUND TASK, never in the foreground
```

It polls until the user decides, then exits with the same code and output as
`mdreview review`, so the completed task IS the outcome: branch on its exit
code with the table below, no further command needed. The user never has to
say "done".

Never run `await` in the foreground of your turn. The no-blocking rule is
absolute; a harness without background tasks simply uses the original flow —
submit, stop, and read the outcome when nudged.

Useful flags:

- `--slug <slug>` — resubmit a revision of an existing document. Always pass
  this when resubmitting, or you will create a second unrelated document.
- `--title <title>` — defaults to the document's first heading.
- `--no-open` — do not launch a browser.

Resubmitting byte-identical content while the review is still pending is a
no-op, so retrying is safe.

## Reading the outcome

When the background watcher completes, or when the user says the review is
done — "done", "approved", "go", "have a look" — read the outcome. For a
completed watcher the outcome is its own exit code and output; on a nudge,
your **first action** is:

```bash
mdreview review <slug>
```

Branch on the **exit code**, not on the text:

| Exit | Meaning | What you do |
| ---- | ------- | ----------- |
| 0 | Approved | Proceed with implementation. |
| 2 | Changes requested | Revise. See below. |
| 3 | No decision recorded yet | Tell the user the review is still outstanding and stop. **Do not proceed.** |
| 4 | Cancelled | Stop and ask the user how they want to proceed. |
| 5 | Server unreachable | Infrastructure problem, not a verdict. Report it; do not treat it as approval. |

Exit 3 is the one to be careful about. It means the user nudged you before
actually clicking anything. Absence of requested changes is **not** approval —
say so and wait.

## Handling requested changes

Exit 2 prints each open comment with its reference, line range, the quoted
source it refers to, and the user's note:

```
STATUS: changes_requested   VERSION: 1   OPEN: 2

--- open comments (2) ---

[C1] L12-14
  > ## Phase 2: migrate the table in one shot
  -> split this per tenant, we cannot hold the lock that long

[C2] L30
  > wrap the migration in a transaction
  -> BigQuery has no DDL transactions
```

Everything you need is in that output; you do not need to re-read the file to
understand the feedback. A comment may target a single line — including one line
inside a fenced code block — so read the line range, not just the quote.

Then:

1. Edit the file to address each comment.
2. Resubmit for another round, passing the same slug:
   ```bash
   mdreview submit PLAN.md --slug <slug>
   ```
   Resubmitting supersedes the comments you just read; there is no bookkeeping
   step, and you never mark a comment as done.
3. Tell the user a new version is up, and stop again.

If you disagree with a comment, do not silently work around it. Say so in your
message to the user and let them decide.

## Write documents that use the renderer

The review page renders more than plain prose. Using these makes a plan easier
to review, so prefer them where they fit:

- **Task lists** — `- [x] done` / `- [ ] todo` render as real checkboxes. Good
  for a phased plan. They are read-only for the user, so do not expect them to
  tick anything; they will comment instead.
- **Diagrams** — a fence tagged `mermaid` renders as a diagram. Good for a flow,
  a state machine, or a dependency graph. If it fails to parse the user sees the
  source, so a broken diagram is visible rather than silently missing.
- **Tables, blockquotes, code fences** all render normally.

Every heading, paragraph, list item, table, diagram and code block is separately
commentable, so structure the document in small blocks rather than long
paragraphs — it gives the user precise places to attach feedback.

## The three views

Worth mentioning to the user if they are looking for something:

- **Rendered** — the default; click any block to comment.
- **Source** — numbered lines; click one, shift-click to extend. This is how
  they comment on a single line inside a code block.
- **Changes** — a diff against the previous version. Appears once a document has
  two versions, and is how they check that a revision did what you claimed.

## Other commands

```bash
mdreview await <slug>        # background watcher: exits with the outcome
mdreview list --pending      # documents awaiting a decision
mdreview status <slug>       # one-line summary
mdreview open <slug>         # reopen the review page
```

## Reviewing from a phone

If the user wants to review on another device on the same network, the server
must be started explicitly on that interface:

```bash
mdreview serve --host <private-ip> --allow-lan
```

It prints a URL containing a capability token; the user opens that one link and
the token is remembered. Requests from another machine without the token are
refused. Loopback never needs the token, so your own commands are unaffected.

Find the address with `ipconfig getifaddr en0` on macOS. It changes with DHCP, so
if a previously working link stops loading, the address has probably moved.

## Notes

- The server starts itself on first use. There is no daemon to manage.
- Each submission is an immutable version. Comments on an older version are
  marked outdated rather than moved, so nothing you resubmit can corrupt
  feedback the user already wrote.
- Everything is local and single user. It listens on loopback unless explicitly
  told otherwise.
