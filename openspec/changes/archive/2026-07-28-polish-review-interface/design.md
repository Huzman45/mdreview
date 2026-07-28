## Context

A refinement pass over the interface, driven by looking at it against the operator's
real documents rather than test fixtures. That distinction mattered: the fixtures had
short inline code and narrow tables, so the worst defect present was invisible to
them.

## Goals / Non-Goals

**Goals:**

- Fix the horizontal overflow, and make it impossible to reintroduce silently.
- Remove the things that read as unfinished: duplicated title, ambiguous navigation,
  ragged index, adrift diff numbers.
- Keep a way to review the interface by eye that does not need rebuilding each time.

**Non-Goals:**

- A redesign, new routes, or any change to review semantics.
- Pixel-perfect snapshot comparison.
- Widening browser support.

## Decisions

### D1. Inline code wraps, because the alternative broke the page

`white-space: nowrap` was added to stop short code spans breaking mid-token. It reads
slightly better for short spans and is catastrophic for long ones: an identifier that
cannot break forces the page wider than the screen, measured at 1121px inside a
390px viewport.

`overflow-wrap: anywhere` replaces it. Long identifiers now break at an arbitrary
point, which is less pretty than breaking at a token boundary and vastly better than
a page that scrolls sideways.

Inline code also gets its own background token rather than sharing the sunken-surface
token used by panels. Sharing them forced a compromise that made code chips too heavy
against body text.

### D2. Overflow is a tested property, not a style opinion

This bug shipped twice, and both times the tests passed, because no assertion about
markup can detect it. The check measures `scrollWidth - clientWidth` in a real
browser on every page at four widths, and reports the widest offending element so a
failure is actionable rather than merely true.

The tests skip when no browser is installed, so the suite stays runnable without a
~90MB download.

*Alternative considered:* screenshot snapshot comparison. Rejected — it fails on font
rendering differences and would need constant re-baselining, while catching this
particular defect only incidentally. Asserting the layout property directly is both
narrower and more reliable.

### D3. One headline per page

The chrome title repeated the document's own first heading at a larger size, so two
headlines competed and roughly 100px was spent before any content. The chrome title
becomes a breadcrumb: smaller, muted, and clamped to one line on a phone where the
cost is worst.

The document's own heading is not suppressed. Removing it would take it out of the
set of commentable blocks, so the reviewer could no longer comment on the title —
trading a cosmetic problem for a functional regression.

### D4. Two choices must not look like one control

Version numbers and view names were rendered as one row of visually identical pills,
with the current version and the current view both filled blue. Views are now a
segmented control, which is what a set of mutually exclusive views is; versions are a
separate labelled group. The label carries the meaning that pill shape cannot.

### D5. A fixed status column, so titles align

Index titles started at different offsets because "Approved" is wider than "Pending",
which read as carelessness. The status column is now a fixed width. Long project
paths truncate rather than dominating the row.

### D6. Diff numbers belong to their content

The two line-number columns sat far from the text with a wide gutter, so a pair of
numbers read as two stray columns. They are narrower and adjacent, and a changed
row's tint now covers the gutter, so a change reads as one band across the row.

## Risks / Trade-offs

- **`overflow-wrap: anywhere` can break an identifier mid-token.** → Accepted; the
  alternative is a page wider than the screen. It only applies when the span cannot
  otherwise fit.
- **The browser tests add a large dev dependency.** → Confined to a dev group and
  skipped when absent, so a fresh clone still runs the suite.
- **The breadcrumb is clamped on phones, so a long title is truncated there.** →
  Accepted; on the rendered view the full title appears immediately below as the
  document's own heading.
- **Screenshots are not asserted, only the layout property.** → Visual regressions
  still need a human eye, which is what the harness is for. Automating that judgement
  reliably is a much larger undertaking.

## Migration Plan

Presentation only. No schema, route, or contract change; nothing to migrate and
nothing to roll back beyond reverting the stylesheet.

## Open Questions

Whether the harness should be wired into the checks and its output diffed, rather
than run on demand. That needs a stable rendering environment to avoid false
positives, so it is left manual for now.
