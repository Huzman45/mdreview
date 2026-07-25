Each numbered group is delivered as one pull request, in this order. The tool runs after
every group.

## 1. Task list checkboxes

- [x] 1.1 Add the `mdit-py-plugins` dependency and enable the `tasklists` plugin in
  `build_parser`, with checkboxes disabled
- [x] 1.2 Confirm the plugin composes with block anchoring: `list_item_open` keeps its
  `token.map`, and the existing class is preserved rather than overwritten
- [x] 1.3 Style checkboxes so ticked and unticked items are distinguishable, and dim the
  text of completed items
- [x] 1.4 Tests: `- [x]` and `- [ ]` render as checked and unchecked inputs; no literal
  `[x]` remains; inputs are disabled; per-bullet anchoring still yields one block per
  item with correct line ranges

## 2. Diagram rendering

- [x] 2.1 Vendor `mermaid.min.js` into static assets
- [x] 2.2 Mark fences whose info string is a supported diagram language with a diagram
  class in `render.py`, preserving the fence source and the anchored line range
- [x] 2.3 Add client-side upgrading: detect diagram blocks, inject the library only if
  at least one is present, and render with `securityLevel: 'strict'`
- [x] 2.4 Fall back to showing the source with a "could not render" note when parsing
  fails or the library is unavailable
- [x] 2.5 Pass the active colour scheme to the diagram theme, and re-render on theme
  change
- [x] 2.6 Tests: a `mermaid` fence is marked and keeps its line range; other fences are
  untouched; the library is referenced only on pages containing a diagram; the fence
  source survives in the markup
- [x] 2.7 Verify in a browser that a real diagram renders, and that a malformed one
  falls back to source

## 3. Theme preference

- [x] 3.1 Restructure the stylesheet so dark tokens apply via both the media query and
  an explicit `[data-theme="dark"]`, with `[data-theme="light"]` forcing light
- [x] 3.2 Add the three-state control to the base template top bar
- [x] 3.3 Persist the choice in `localStorage` and apply it before first paint with an
  inline head script
- [x] 3.4 Reflect the active choice in the control, and update `theme-color` to match
- [x] 3.5 Tests: the control is present on every page type; the inline script runs
  before the stylesheet; both explicit attributes are honoured by the stylesheet
- [x] 3.6 Verify in a browser that light, dark and system all apply, persist across
  navigation, and produce no flash on load

## 4. Raw line view

- [ ] 4.1 Add a `GET /d/{slug}/v/{n}/raw` route rendering numbered source lines, 404 for
  unknown slug or version
- [ ] 4.2 Reuse the existing sidebar, comment form and lifecycle gate, so a decided or
  superseded version offers no form
- [ ] 4.3 Add line selection: click for one line, shift-click to extend to a contiguous
  range, feeding the existing `line_start`/`line_end` fields
- [ ] 4.4 Cross-link the rendered and raw views for the same version
- [ ] 4.5 Tests: every line is listed with its 1-based number; markdown appears as
  literal source; a comment on one line inside a fence stores that line and quotes
  exactly it; a range comment quotes exactly those lines; a raw comment is structurally
  identical to a block comment; out-of-bounds is rejected; no form on decided or
  superseded versions
- [ ] 4.6 Verify by hand that a single line inside a fenced block can be commented on

## 5. Version diff view

- [ ] 5.1 Implement a unified line diff over two versions using `difflib`, returning
  typed rows with both sides' line numbers and limited surrounding context
- [ ] 5.2 Add a `GET /d/{slug}/diff/{a}/{b}` route, 404 for unknown document or version
- [ ] 5.3 Template the diff with added, removed and context styling, and a clear
  "nothing changed" state
- [ ] 5.4 Link a version to the comparison with its predecessor, and offer no link when
  there is only one version
- [ ] 5.5 Ensure the diff carries no comment form and no decision control
- [ ] 5.6 Tests: added, removed and context rows are classified correctly; non-adjacent
  versions compare; identical content reports no change; line numbers belong to the
  correct side; unknown document and version are 404; no form present
- [ ] 5.7 Verify by hand against two real versions of a document

## 6. Integration

- [ ] 6.1 Move shared top bar, theme control and view links into the base template so
  the four page types cannot drift
- [ ] 6.2 End-to-end test: submit, comment from the raw view on a line inside a fence,
  request changes, revise, resubmit, inspect the diff, approve
- [ ] 6.3 Update the README with the new views, the theme control, checkbox and diagram
  support, and the vendored asset
- [ ] 6.4 Full suite, lint, format, and a browser pass at desktop and phone width in
  both colour schemes
