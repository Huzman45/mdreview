## Why

An openspec change is agent-authored markdown whose whole purpose is to be
approved by a human before implementation — mdreview's exact shape — but a
change is a directory of 4–7 files and mdreview reviews one file. The
`openspec-review-mode` investigation weighed five options and recommended
this one; the decision was confirmed against working prototypes of the
alternatives (branch `proto/openspec-review`): the assembled single document
won for being the simplest shape that does not clutter the UI.

Two requests came out of that review and are part of this change:

1. The boundary between bundled files must be clearly visible on the page.
2. The agent-facing loop must be ergonomic end to end — globs in, and
   feedback that points at the source file, not at a line in an assembly
   the agent then has to decode by hand.

## What changes

- `mdreview submit` accepts several paths. One path behaves exactly as
  today. Several are assembled deterministically: each file contributes a
  `# <path>` heading followed by its content, in argument order.
- With several files and no `--slug`/`--title`, both default from the
  files' common parent directory name — `mdreview submit change/*.md`
  needs no further options.
- The review page visibly separates top-level parts: any `<h1>` after the
  first opens a new part with a rule above it. This is generic multi-part
  styling, not openspec awareness.
- `review` and `await` reports map each comment back to its source:
  `[C2] L204 (specs/agent-cli/spec.md:8)`. The mapping is derived from the
  assembly headings in the document content, fetched once per report; the
  server stays ignorant of assembly.
- The server exposes a version's raw content
  (`GET /api/documents/{slug}/versions/{n}/content`) so the CLI can derive
  that mapping. This is the only server change.
- The md-review skill gains a short section on reviewing a file set, and
  `/opsx-propose` ends by submitting the change bundle for review.

## What does not change

- Storage, schema, and the review data model: the server stores one
  markdown document, as ever.
- Rendering: `# <path>` is an ordinary heading; deltas read as prose.
- openspec: no approval state is written back; the mdreview decision is
  the gate.

## Impact

- `agent-cli` spec: multi-file submission, source mapping in reports.
- `markdown-review-page` spec: part separation.
- `agent-skill` spec: the skill documents the file-set flow.
- Code: `cli.py`, `report.py`, `api.py` (one endpoint), `app.css`,
  `skill/md-review/SKILL.md`, `.opencode/commands/opsx-propose.md`.
