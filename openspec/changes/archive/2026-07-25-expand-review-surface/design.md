## Context

Five additions to the review surface. Two were recorded as open questions in the
original design and are cheap now precisely because of a decision made then: comments
anchor to **line ranges**, not to block identifiers, so a line-precise view and a diff
view need no schema change and no migration.

The constraints from the original design still hold and shape everything here:
document content is untrusted, the agent owns the file, versions are immutable, and the
page must stay readable on a phone.

## Goals / Non-Goals

**Goals:**

- Render the markdown constructs that plan documents actually use.
- Let feedback reach text that block anchoring cannot isolate.
- Make a revision's changes visible, so an `outdated` comment can be acted on.
- Let the reader override the system colour scheme.
- Keep the offline guarantee and the untrusted-input posture intact.

**Non-Goals:**

- Editing documents in the browser, including interactive checkboxes.
- Commenting on a diff, or diffing across documents.
- Authoring or previewing diagrams.
- Everything in the proposal's Non-goals section.

## Decisions

### D1. Task lists come from a plugin, and stay disabled

`mdit-py-plugins` provides a `tasklists` plugin that converts `- [x]` into a real
`<input type="checkbox">`. Verified that it preserves `token.map` on `list_item_open`,
so per-bullet anchoring is unaffected.

Checkboxes are rendered **disabled**. A clickable checkbox has no honest semantics
here: writing back would break the immutable-version invariant that comment anchoring
rests on, and toggling without writing back would show the reviewer state that neither
persists nor reaches the agent.

The plugin sets `class="task-list-item"` on the item, and the anchoring code already
appends to an existing class rather than overwriting it, so the two compose.

### D2. Diagrams render client-side, with the fence preserved

The server does not render diagrams. It marks a `mermaid` fence with a class and leaves
the source in the page; the browser upgrades it. This keeps `render.py` pure and means
a diagram that fails leaves its source visible, satisfying the "never hide content"
requirement for free.

Mermaid is 3.5 MB. It is **vendored** rather than loaded from a CDN, keeping the
offline guarantee the project already makes for htmx, and **lazy-loaded**: the script is
injected only when a page actually contains a diagram, so ordinary documents pay
nothing.

`securityLevel: 'strict'` is set, which sanitises markup in diagram labels. This
matters because diagram source is agent-authored and therefore untrusted, exactly like
document prose.

The diagram wrapper is the anchored element, so a diagram remains commentable — often
the thing a reviewer most wants to question.

*Alternative considered:* server-side rendering to SVG via a headless browser.
Rejected — it would add a heavyweight dependency and a subprocess to a tool whose whole
premise is that it starts instantly with no setup.

### D3. The raw view reuses the comment anchor unchanged

The raw view lists numbered lines and posts to the **same** comment endpoint with the
same `line_start`/`line_end` fields. There is no new storage, no new validation, and no
way for a raw comment to be distinguishable from a block comment — which is the point,
since the agent should not have to care which view produced the feedback.

Selection is click for one line, shift-click to extend to a range. This is the
interaction people already know from diff views and file browsers.

The raw view honours the same lifecycle gate as the rendered view: no comment form on a
decided or superseded version. Two views that disagreed about whether a round is open
would be a bug.

### D4. Diff is a unified line diff from `difflib`

`difflib.SequenceMatcher` over the two versions' lines, presented as a unified diff with
line numbers on both sides. Python's standard library is sufficient; there is no reason
to add a dependency.

Unified rather than side-by-side, because side-by-side is unreadable at phone width and
this tool is used from a phone.

A diff is **read-only**. It describes a relationship between two versions and belongs to
neither, so anchoring a comment to it would have no valid version to attach to.

### D5. Theme is an explicit override layered over the media query

The stylesheet keeps `@media (prefers-color-scheme: dark)` for the default and adds
`[data-theme="dark"]` / `[data-theme="light"]` on the root element for an explicit
choice. Three states: `light`, `dark`, `system`, stored in `localStorage`.

The stored preference is applied by a small **inline** script in `<head>`, before the
stylesheet paints. A deferred script would produce a visible flash of the wrong theme on
every load, which is the single most noticeable way to get this wrong.

*Alternative considered:* persisting the preference server-side in SQLite. Rejected —
the theme is a property of the reader and their device, not of the review data, and it
would mean a write to the database on a UI toggle.

### D6. Shared page furniture moves into the base template

Four page types now need the same top bar, theme control, and view links. That furniture
moves into the base template rather than being repeated, so the raw and diff views
cannot drift from the rendered view.

## Risks / Trade-offs

- **3.5 MB of vendored JavaScript in git.** → One-off cost, lazy-loaded so it is not
  paid per page view. The alternative was breaking the offline guarantee for every user
  to save repository size once.
- **Mermaid renders untrusted input in the browser.** → `securityLevel: 'strict'`, and
  the fence source is what is preserved on failure, so a hostile diagram degrades to
  visible text rather than executing.
- **The raw view invites line-precise comments that a revision immediately outdates.**
  → Accepted; this is the existing `outdated` behaviour and the new diff view is what
  makes it tractable.
- **Two commenting surfaces could diverge in behaviour.** → Both post to the same
  endpoint and share the same lifecycle gate, and tests assert a raw comment is
  structurally indistinguishable from a block comment.
- **A large diff is slow to render or unreadable.** → Context lines are limited around
  each change rather than printing the whole document.
- **An inline theme script is an exception to keeping JavaScript in a static file.** →
  Deliberate and confined to a few lines; the flash it prevents is otherwise unavoidable.

## Migration Plan

No data migration; no schema change. All new routes are read-only additions except the
raw view's comment form, which reuses the existing endpoint. Rollback is reverting the
templates and static assets.

Delivery is a Graphite stack, one feature per PR, tracer-bullet ordered so the tool runs
after each.

## Open Questions

None blocking. Deferred: whether the diff view should offer a whole-document mode rather
than limited context, which depends on how large plan documents actually get in practice.
