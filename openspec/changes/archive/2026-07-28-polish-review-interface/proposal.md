## Why

Reviewing the interface against real documents rather than test fixtures exposed a
bug that had shipped twice: inline code carried `white-space: nowrap`, so a long
identifier could not break and pushed the page far wider than the screen. Measured
at 1121px inside a 390px viewport — the review page was unusable on a phone for any
document containing a long identifier, which is most of them.

The same pass showed several things that read as unfinished: the document title
appeared twice at two sizes, version numbers and view names were rendered as one
row of identical pills despite being different choices, index titles did not align
because the status pill varied in width, and the diff's line numbers sat adrift
from the text they belonged to.

## What Changes

- Inline code wraps. Long identifiers break rather than widening the page.
- **A requirement that nothing may exceed the viewport width**, on every page type
  at every supported width, checked by a real browser rather than by inspecting
  markup — the only way this class of bug is catchable.
- The document title becomes a breadcrumb rather than a second headline competing
  with the document's own heading, and is clamped to one line on a phone.
- Views become a segmented control; version numbers become a separate labelled
  group, so two different choices no longer look like one.
- Index rows align on a fixed status column, tighten, and truncate long paths.
- Diff line numbers move next to the content, and a changed row's tint covers the
  gutter so a change reaches the edge of the row.
- Quieter disabled comment button, stronger blockquote edge, tighter vertical
  rhythm, and a less shouty selection label.
- A screenshot harness covering every page, width and colour scheme, kept in the
  repository so the interface can be reviewed by eye repeatedly.

## Capabilities

### New Capabilities

- `responsive-layout`: fitting the viewport at every supported width, on every page
  type, in both colour schemes.

### Modified Capabilities

None. This changes presentation and fixes a layout defect; no reviewed behaviour,
route, or stored data changes.

## Non-goals

- **Redesigning the interface.** This is refinement of what exists, not a new look.
- **Changing what any page does.** No new routes, controls, or review semantics.
- **Supporting browsers older than those already required.** The stylesheet already
  depends on `color-mix()` and `:has()`.
- **Pixel-perfect screenshot comparison.** Snapshot diffing would fail on font
  rendering; the automated check is the layout property that actually matters.

## Impact

- Stylesheet, the view-navigation partial, and the sidebar label.
- A new browser-driven test module, skipped when the browser is absent so the suite
  still runs without it.
- A new development dependency on Playwright, and a screenshot script under
  `scripts/`.
- No change to the database, the API, the CLI, or the agent-facing contract.
