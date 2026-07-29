## Why

The source view already anchors a comment to any contiguous range: click a
line, shift-click to extend. The rendered view — the one people actually read —
can only select a single block, so feedback that spans a paragraph and the list
after it forces a detour through the source view to say one thing.

## What Changes

- Shift-click in the rendered view extends the selection from the anchored
  block to the clicked block, exactly the interaction the source view already
  has. The comment anchors to the span from the first covered line to the last.
- Every block inside the span is highlighted, so what the note will cover is
  visible before it is written.
- Presentation only: comments already store `(line_start, line_end)` and the
  API accepts arbitrary ranges, so nothing changes in storage, API, or CLI.

## Capabilities

### Modified Capabilities

- `markdown-review-page`: block selection grows range extension; anchoring and
  rendering requirements are untouched.

## Non-goals

- **Discontiguous selection.** A comment is one thought about one region;
  cmd-click multi-select is a different feature with a different anchor model.
- **Changing the source view**, which already behaves this way.
- **Touching the anchor model.** A range that happens to cover several blocks
  is stored no differently from one drawn in the source view.

## Impact

- `static/app.js` and a browser test; no server, schema, or CLI change.
