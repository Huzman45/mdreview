## Why

The review page reads well for prose but three things it cannot express are common
in the plan documents it exists to review: task lists render as literal `[x]`, and
diagrams render as unhighlighted source. Two limitations recorded as open questions
in the original design have also now been hit in practice — feedback cannot target a
single line inside a fenced code block, and there is no way to see what actually
changed between two versions, which makes an `outdated` comment hard to act on.

Finally, colour scheme follows the operating system with no way to override it, which
is wrong in the common case of a bright room and a dark OS theme.

## What Changes

- Markdown task lists render as real checkboxes, checked or unchecked, rather than
  literal bracket text. They are **read-only**: the agent owns the file, and the page
  must not silently edit a document that is about to be revised.
- Fenced blocks tagged as a supported diagram language render as a diagram, with the
  source shown instead if it fails to parse, so a malformed diagram never hides
  content.
- A **raw line view** shows the document as numbered source lines, each individually
  selectable, so a comment can target one line inside a fence or one line of a
  wrapped paragraph. This is the deferred limitation of block-only anchoring.
- A **diff view** compares any two versions of a document, so a reviewer can see what
  a revision actually changed and an agent's claim to have addressed a comment can be
  checked.
- A **theme control** offers light, dark, or follow-the-system, remembered across
  visits, replacing the current system-only behaviour.

## Capabilities

### New Capabilities

- `diagram-rendering`: turning a fenced diagram block into a rendered diagram in the
  browser, including asset delivery, failure fallback, and the security posture for
  rendering untrusted diagram source.
- `raw-line-view`: presenting a version as numbered source lines and anchoring
  comments to an arbitrary line range, including ranges no rendered block covers.
- `version-diff`: comparing two versions of a document and presenting what changed.
- `theme-preference`: choosing and remembering light, dark, or system colour scheme.

### Modified Capabilities

- `markdown-review-page`: task list items render as checkbox controls rather than
  literal text, and the page offers navigation to the raw and diff views.
- `block-comments`: a comment's anchor is no longer required to correspond to a
  rendered block, only to a valid line range within the version.

## Non-goals

- **Editing documents in the browser.** Checkboxes are read-only. Nothing on the page
  mutates document content.
- **Interactive or mutable checkbox state.** Ticking a box would either break the
  immutable-version invariant that comment anchoring depends on, or store state the
  agent is never told about.
- **Diagram editing or live preview.** Diagrams are rendered, not authored.
- **Three-way or semantic diffs.** A line diff between two versions is sufficient to
  answer "what changed".
- **Commenting on a diff.** Comments anchor to a version, not to a comparison; a diff
  is for orientation.
- **Per-document theme.** The theme is a property of the reader, not of a document.

## Impact

- Rendering gains a markdown plugin for task lists and a client-side diagram library,
  delivered as a vendored asset and fetched only by pages that contain a diagram.
- New read-only routes for the raw and diff views. The comment API is unchanged: the
  raw view reuses the existing line-range anchor, which is why this needs no schema
  change.
- The stylesheet gains an explicit theme override alongside the existing media query,
  and the page must set the theme before first paint to avoid a flash of the wrong one.
- New runtime dependency `mdit-py-plugins`. Diagram rendering adds a vendored
  JavaScript asset of a few megabytes, which is why it is lazy-loaded.
