## Context

`static/rawlines.js` established the interaction: click anchors, shift-click
extends, the pair of hidden form fields carries the range. The rendered view's
`static/app.js` selects exactly one block. The anchor model never cared — a
comment stores a line range, and blocks are just line ranges with prose inside.

## Goals / Non-Goals

**Goals:** the same extend gesture in both views; visible coverage of the
whole span before commenting.

**Non-Goals:** discontiguous selection; any storage or API change.

## Decisions

### D1. The range is the union of the anchor block and the clicked block

Shift-click sets the range to `[min(starts), max(ends)]` of the anchor and the
target. Clicking above the anchor extends upward, mirroring the source view's
`select(anchor, n)` with min/max normalisation. The anchor survives further
shift-clicks, so the reviewer can grow or shrink the span from the same fixed
point rather than the range creeping with every click.

### D2. Highlight covered blocks, outermost wins

Blocks nest (a list item inside a list). Painting every block whose lines fall
inside the span would double-tint nested children under a painted parent, so a
block is painted only when it is covered and no ancestor of it is painted.
Between siblings this still marks everything the span crosses; the visual
answer to "what will this note cover" stays exact.

### D3. Intervening blocks join the range implicitly

The span runs by line numbers, so any block between the anchor and the target
is inside it whether or not it was clicked — same as the source view, where the
lines between two shift-clicked lines are selected. This is the property that
makes the gesture mean "from here to there" rather than "these two things".

### D4. A plain click resets to a single block

Plain click always starts a new single-block selection (or toggles the sole
selected block off, as today). Shift-click with no anchor behaves as a plain
click, mirroring `rawlines.js`.

## Risks / Trade-offs

- A span can cover a *container* only partially — anchoring on a list's second
  item leaves the first outside the range. That is correct, not a defect: the
  quote takes exactly the covered lines, and painting only fully-covered
  blocks means the highlight never promises more than the anchor delivers.
- Shift-click normally extends the browser's text selection; suppressed on
  mousedown exactly as the source view already does.
