## Why

The margin is a single stacked list: every note in creation order, wherever
its target happens to be. Reading feedback on a long document means holding a
mapping in your head — C3 is about the fence two screens down — which is
exactly the indirection a margin exists to remove. A marked-up proof puts the
remark beside the passage.

## What Changes

- **Each note sits beside the text it annotates.** In the two-column layout,
  a note's vertical position follows its anchor: the block containing its
  first line, proportionally within multi-line blocks (a note on line 40 of a
  60-line fence sits two-thirds of the way down it), and the exact line in
  the source view.
- **Overlapping notes yield downward.** Notes are taller than the lines they
  point at; when several target the same region, the first holds the anchor
  and the rest follow beneath it in order.
- **The comment form joins the choreography.** Idle, it parks after the last
  note; with a selection, it moves beside the selected region, so writing
  happens where the eyes are.
- **Under 62rem nothing changes.** The stacked list below the prose remains;
  "beside" has no meaning in one column.
- Hovering a note highlights its target again — the existing highlight
  plumbing had been left pointing at a class the redesign renamed, so it is
  rewired rather than rebuilt.

## Capabilities

### Modified Capabilities

- `markdown-review-page`: the margin's presentation gains anchoring; the
  responsive fallback is stated.

## Non-goals

- **Leader lines or connectors** between note and text. Alignment carries
  the association; lines are chartjunk at this density.
- **Collapsing or truncating notes** to force perfect alignment. When space
  runs out, notes flow downward; every note stays fully readable.
- **Re-anchoring.** Where a note points is the store's concern, untouched.

## Impact

- A new `static/anchors.js`, margin CSS (relative container, absolute
  notes in the wide layout), the base template's script includes, the dead
  hover selector in `app.js`, and a browser test module.
