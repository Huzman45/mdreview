## Context

The margin is a 15rem grid column, sticky, holding notes in creation order.
Anchors are line ranges; blocks carry `data-line-start`/`data-line-end` in the
rendered view and lines carry `data-line` in the source view. This is a
layout problem, not a styling one: note positions depend on rendered
geometry (fonts, images, diagrams, viewport), which CSS alone cannot read.

## Goals / Non-Goals

**Goals:** a note's vertical position encodes its anchor; overlap resolves
readably; the narrow layout is untouched.

**Non-Goals:** connectors; virtualised rendering; anchoring on pages without
a margin (diff).

## Decisions

### D1. JavaScript measures, CSS only paints

Positions come from a layout pass in `anchors.js`: resolve each note's
anchor element, read its offset, sort notes by anchor position, then walk
down assigning `top = max(anchorTop, previousBottom + gap)`. CSS switches
`.margin` from sticky to relative and notes to absolute in the wide layout —
sticky dies here by necessity, since a note tied to its passage cannot also
follow the scroll.

### D2. Anchor resolution is line-first, block-second, proportional inside

The note's `line_start` finds its anchor: the exact `.mdr-line` when the
view has lines (source), else the innermost block whose range contains the
line. Within a multi-line block the offset interpolates linearly between the
block's top and bottom by line fraction, so a note into the middle of a long
fence points at the middle, not the fence's first line. A note whose line no
element covers (possible if rendering skipped a construct) falls back to the
top of the prose rather than disappearing.

### D3. Overlap yields downward, anchors win in document order

Notes sorted by anchor position each take the higher of their anchor and the
previous note's bottom plus a fixed gap. The first note on a crowded passage
holds the exact anchor; followers queue beneath. Nothing is ever hidden or
clipped — the margin's height is raised to the last note's bottom so the
sheet grows instead of overflowing.

### D4. The form is one more item in the same layout

Idle, the form sorts after every note (it has no anchor); selecting a region
gives it that anchor, and it competes in the same pass — ties resolve with
existing notes first, so the form lands after the notes it would join. One
algorithm, no special cases in the placement itself.

### D5. Re-layout on the events that change geometry

Initial load, htmx sidebar swaps (`htmx:afterSwap`), viewport resize, and a
`ResizeObserver` on the prose — which is what catches diagrams rendering,
images arriving, and fonts swapping, all of which move every offset below
them. The pass is idempotent and cheap (tens of notes, one read phase, one
write phase), so re-running it is the simplicity play. Position transitions
are enabled only after the first pass, so notes glide when nudged but never
animate in from nowhere on load.

### D6. DOM order stays creation order

Absolute positioning frees visual order from DOM order. The DOM keeps
creation order (stable references, stable tab order); only the paint moves.

## Risks / Trade-offs

- **Losing sticky notes-follow-scroll.** Inherent to the feature: a note
  cannot both follow the scroll and sit beside its passage. The hover
  highlight ties the two together once they are on screen.
- **A burst of overlapping notes pushes later ones far below their
  anchors.** Accepted: order is preserved, everything stays readable, and
  the alternative (overlap or truncation) is strictly worse.
- **Layout thrash on pathological documents.** The pass separates reads
  from writes and runs on discrete events, not scroll, so cost is bounded.
