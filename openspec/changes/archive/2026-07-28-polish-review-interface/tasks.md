## 1. Fix the overflow and prevent its return

- [x] 1.1 Replace `white-space: nowrap` on inline code with wrapping that breaks a
  long identifier rather than widening the page
- [x] 1.2 Give inline code its own background token, so it is not tied to the panel
  surface that made it too heavy
- [x] 1.3 Add browser-driven tests asserting no page exceeds the viewport at phone,
  tablet portrait, tablet landscape and laptop widths
- [x] 1.4 Report the widest offending element on failure, so it is actionable
- [x] 1.5 Skip the browser tests when no browser is installed

## 2. Refinement

- [x] 2.1 Demote the chrome title to a breadcrumb, clamped to one line on a phone,
  without suppressing the document's own heading
- [x] 2.2 Make views a segmented control and versions a separate labelled group
- [x] 2.3 Align index titles on a fixed status column, tighten rows, truncate paths
- [x] 2.4 Move diff line numbers beside their content and extend a changed row's tint
  across the gutter
- [x] 2.5 Quieter disabled comment button, stronger blockquote edge, tighter rhythm,
  clearer selection label

## 3. Verification

- [x] 3.1 Add a screenshot harness covering every page, width and colour scheme
- [x] 3.2 Capture before and after, and confirm the overflow is gone in all 32
  combinations
- [x] 3.3 Full suite, lint, format
