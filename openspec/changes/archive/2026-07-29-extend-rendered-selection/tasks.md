## 1. Selection

- [x] 1.1 Track the anchor block; shift-click extends the selection to the
  union of the anchor's and target's line ranges
- [x] 1.2 Paint every fully covered block whose ancestors are not painted
- [x] 1.3 Plain click resets to single-block selection; shift-click with no
  anchor is a plain click; Escape and outside-click clear as before
- [x] 1.4 Suppress the browser text selection on shift-mousedown over a block

## 2. Verification

- [x] 2.1 Browser tests: extend down, extend up, intervening blocks painted,
  nested blocks not double-painted, form fields carry the combined range,
  posted comment anchors to it
- [x] 2.2 Full suite, ruff, screenshot harness
