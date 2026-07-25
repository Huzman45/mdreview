---
name: md-review
description: Publish a plan, design, or proposal document for the user to review in a browser, then read their decision and line-level comments back. Use whenever you have written a plan the user should approve before you implement it, or when they ask you to "put this up for review", "let me review that", or "send it to mdreview". Also use on resume, when the user says the review is done, to pick up their decision.
license: MIT
compatibility: Requires the mdreview CLI on PATH.
metadata:
  author: fjvillamarin
  version: "1.0"
---

# Reviewing a document with mdreview

`mdreview` turns a markdown file into a web page where the user can comment on
individual blocks and either approve it or send it back. You submit, you stop,
they review, they nudge you, you read the outcome.

**You never block waiting for the review.** Submit, tell the user the URL, and
end your turn.

## Submitting

Write the document to a file first, then:

```bash
mdreview submit PLAN.md
```

This prints the review URL, opens it in the user's browser, and returns
immediately. Then:

1. Tell the user the URL and that you are waiting on their review.
2. **Stop.** Do not start implementing. Do not ask follow-up questions that
   presume approval.

Useful flags:

- `--slug <slug>` — resubmit a revision of an existing document. Always pass
  this when resubmitting, or you will create a second unrelated document.
- `--title <title>` — defaults to the document's first heading.
- `--no-open` — do not launch a browser.

Resubmitting byte-identical content while the review is still pending is a
no-op, so retrying is safe.

## Reading the outcome

When the user says the review is done — "done", "approved", "go", "have a look"
— your **first action** is:

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

Exit 2 prints each unresolved comment with its reference, line range, the quoted
source it refers to, and the user's note:

```
STATUS: changes_requested   VERSION: 1   UNRESOLVED: 2

--- unresolved comments (2) ---

[C1] L12-14
  > ## Phase 2: migrate the table in one shot
  -> split this per tenant, we cannot hold the lock that long

[C2] L30
  > wrap the migration in a transaction
  -> BigQuery has no DDL transactions
```

Everything you need is in that output; you do not need to re-read the file to
understand the feedback.

Then:

1. Edit the file to address each comment.
2. Mark what you addressed:
   ```bash
   mdreview resolve <slug> C1 C2
   ```
3. Resubmit for another round, passing the same slug:
   ```bash
   mdreview submit PLAN.md --slug <slug>
   ```
4. Tell the user a new version is up, and stop again.

If you disagree with a comment, do not silently resolve it. Say so in your
message to the user and let them decide.

## Other commands

```bash
mdreview list --pending      # documents awaiting a decision
mdreview status <slug>       # one-line summary
mdreview open <slug>         # reopen the review page
```

## Notes

- The server starts itself on first use. There is no daemon to manage.
- Each submission is an immutable version. Comments on an older version are
  marked outdated rather than moved, so nothing you resubmit can corrupt
  feedback the user already wrote.
- Everything is local, on loopback, single user.
