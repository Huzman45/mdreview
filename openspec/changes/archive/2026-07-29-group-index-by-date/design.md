## Context

The index was rebuilt (PR #23) around one question — what needs my attention —
splitting Waiting from Decided. The user now asks for date grouping. The two
structures are not in conflict: attention first, time inside it.

## Goals / Non-Goals

**Goals:** scan the decided history by day; change nothing about how waiting
work presents.

**Non-Goals:** undoing the status split; per-session grouping (needs session
identity, a later change).

## Decisions

### D1. Date groups nest inside the status split, they do not replace it

Replacing the split would silently reverse a deliberate, recent design. The
waiting queue keeps its flat, newest-first shape — it is an inbox, usually a
handful of rows, and slicing a handful by day adds headers without adding
orientation. The decided section is where history accumulates, so that is
where days help.

### D2. Grouped by the version's submission time, in local days

Each row already displays and sorts by its latest version's `created_at`;
grouping by anything else (say `decided_at`) would file a row under a day its
own timestamp contradicts. One timestamp drives sorting, display, and
grouping. Buckets are calendar days in the server's local timezone — this is
a single-user tool running on the reviewer's machine, so the server's clock
is the reviewer's clock; UTC bucketing would shift late-evening work into
the wrong day.

### D3. Labels: Today, Yesterday, then dates

"Today" and "Yesterday" are how people actually orient; beyond that, relative
labels ("3 days ago") make worse headers than dates because they age. Within
the current year the year is dropped ("26 July"); older groups carry it
("26 July 2025"). No weekday names — they read well for a week and then
require arithmetic.

## Risks / Trade-offs

- **Group labels age across midnight** on a page left open — "Today" becomes
  wrong at 00:00. Every timestamp on the page already has this property; a
  refresh fixes all of them together.
