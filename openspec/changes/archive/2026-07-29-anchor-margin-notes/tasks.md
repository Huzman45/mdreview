## 1. Layout

- [x] 1.1 `anchors.js`: anchor resolution (line, containing block,
  proportional interpolation, prose-top fallback), sort, downward overlap
  pass, margin height raise
- [x] 1.2 The form participates: idle after the last note, anchored to the
  selection otherwise
- [x] 1.3 Re-layout on load, htmx swap, resize, and prose ResizeObserver;
  transitions only after the first pass
- [x] 1.4 CSS: relative margin and absolute notes in the wide layout only;
  narrow stacked list untouched
- [x] 1.5 Rewire the note hover highlight to the current markup

## 2. Verification

- [x] 2.1 Browser tests: alignment to block, proportional alignment into a
  fence, same-anchor stacking without intersection, source-view line
  alignment, narrow fallback stays static, form moves to selection, swap
  re-layout, hover highlight
- [x] 2.2 Full suite, ruff, screenshot harness
