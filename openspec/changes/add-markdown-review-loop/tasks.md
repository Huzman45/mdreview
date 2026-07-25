Each numbered group is delivered as one pull request in a Graphite stack, in this
order. Groups are ordered tracer-bullet style: the tool runs end to end from group 2
onward, and no group leaves it in a non-running state.

## 1. Scaffold and server runtime

- [x] 1.1 Create the `uv` project: `pyproject.toml` with the `mdreview` package under
  `src/`, the `mdreview` console script entrypoint, and pinned runtime dependencies
  (`fastapi`, `uvicorn`, `jinja2`, `markdown-it-py`, `typer`, `httpx`)
- [x] 1.2 Add dev tooling: `ruff` lint and format config, `pytest` config, and a
  `mise.toml` exposing `serve`, `test`, `lint`, and `fmt` tasks
- [x] 1.3 Implement `config.py`: data directory and database path resolution, default
  port 7391, and environment-variable overrides for both
- [x] 1.4 Implement `db.py`: connection factory setting WAL journal mode and foreign-key
  enforcement, plus the `PRAGMA user_version` migration runner
- [x] 1.5 Implement `migrations.py` with step 1 creating `documents`, `versions`,
  `comments`, and the two indexes exactly as specified in design D9
- [x] 1.6 Implement `models.py`: dataclasses for document, version, and comment, and
  enums for review status and comment state
- [x] 1.7 Implement `server.py`: FastAPI app factory, lifespan hook that opens the
  database and migrates on startup, and a `/healthz` route reporting app and schema
  version
- [x] 1.8 Enforce loopback-only binding, rejecting any non-loopback host at startup
- [x] 1.9 Implement `cli.py` with the Typer app and the `serve` command, supporting
  foreground and detached modes
- [x] 1.10 Implement `client.py`: HTTP client wrapper with lazy autostart — on
  connection refused, spawn a detached server, poll `/healthz` until ready, retry once,
  and exit 5 if it cannot be started
- [x] 1.11 Tests: migration runner is idempotent and incremental; pragmas are applied;
  `/healthz` responds; non-loopback host is refused; autostart spawns and reuses a
  server
- [x] 1.12 Verify by hand: `mise run serve`, confirm `/healthz`, confirm the database is
  created at the expected path with `user_version` set

## 2. Document submission and immutable versions

- [x] 2.1 Implement document and version writes in `store.py`: create document, derive a
  unique slug with a numeric suffix on collision, and record a version with its
  SHA-256 digest
- [x] 2.2 Implement sequential per-document version numbering
- [x] 2.3 Implement digest-based idempotency per design D8: identical content against a
  pending latest version reuses it and reports the reuse; identical content against a
  decided version opens a new version
- [x] 2.4 Reject submissions whose content is empty or whitespace-only
- [x] 2.5 Add `POST /api/documents` accepting content, optional slug, title, project
  path, and session id, returning slug, version number, review URL, and reuse flag
- [x] 2.6 Add `GET /api/documents/{slug}` and `GET /api/documents` with a pending filter
- [x] 2.7 Implement the `submit` CLI command: read the file, send the working directory
  as project path automatically, print the review URL, fail clearly on a missing path
- [x] 2.8 Tests: version 1 creation; sequential numbering; per-document independence;
  digest reuse on pending; new version after a decision; empty content rejected;
  earlier versions unchanged by a later submission; slug collision suffixing
- [x] 2.9 Verify by hand: submit a real markdown file twice unchanged, confirm one
  version; submit modified content, confirm version 2

## 3. Rendered review page with block anchors

- [x] 3.1 Implement `render.py`: `markdown-it-py` configured with HTML disabled, walking
  the token stream and wrapping each top-level block with its `token.map` line range
- [x] 3.2 Return both the rendered HTML and the list of block ranges, so ranges can be
  validated and tested without parsing HTML
- [x] 3.3 Implement link-scheme filtering to neutralise `javascript:` and other
  non-allow-listed targets
- [x] 3.4 Add a `quote_lines` helper extracting the markdown source for a line range
- [x] 3.5 Build the Jinja2 base template and the document template with autoescaping on;
  vendor htmx and a stylesheet into `static/`
- [x] 3.6 Add `GET /d/{slug}` and `GET /d/{slug}/v/{n}` rendering a version with its
  title, version number, status, and project path; 404 for an unknown slug
- [x] 3.7 Add the block-selection JavaScript: click a block to select it and reveal the
  comment form, keyed off the `data-line-start` and `data-line-end` attributes
- [x] 3.8 Implement the `open` CLI command and make `submit` open the browser by default
  with a `--no-open` opt-out
- [x] 3.9 Tests: headings, paragraphs, individual list items, and fences each yield a
  distinct range; ranges lie within content bounds; a range round-trips to its source
  text via `quote_lines`; `<script>` and inline handlers render as text; a
  `javascript:` link target is stripped; unknown slug returns 404
- [x] 3.10 Verify by hand: submit a document with nested lists, tables, and code blocks
  and confirm every block is individually selectable in the browser

## 4. Block comments

- [ ] 4.1 Implement comment writes in `store.py`: allocate the next `Cn` reference per
  version, capture the quoted source at creation, and insert with state `open`
- [ ] 4.2 Validate anchors against version bounds and reject empty bodies
- [ ] 4.3 Implement comment listing per version with state filtering
- [ ] 4.4 Implement resolution by reference: idempotent for already-resolved comments,
  erroring on an unknown reference
- [ ] 4.5 Mark all `open` comments on prior versions `outdated` when a new version is
  recorded, leaving `resolved` comments and all anchors untouched
- [ ] 4.6 Add `POST /api/documents/{slug}/versions/{n}/comments`,
  `GET .../comments`, and `POST .../comments/{ref}/resolve`
- [ ] 4.7 Add the htmx comment form and comment list fragment, rendering bodies as
  escaped plain text beside their anchored blocks
- [ ] 4.8 Tests: comment creation and anchoring; quoted text captured; out-of-bounds
  anchor rejected; empty body rejected; references assigned in order and scoped per
  version; references stable across resolution; resolve idempotent; unknown reference
  errors; new version outdates open comments but not resolved ones; anchors never
  rewritten; HTML in a body is escaped in the page
- [ ] 4.9 Verify by hand: comment on three blocks, resolve one, submit a new version,
  confirm the remaining open comments show as outdated against version 1

## 5. Review decisions

- [ ] 5.1 Implement decision recording in `store.py`: set status, decision note, and
  decision timestamp on a version
- [ ] 5.2 Reject a decision on an already-decided version as a conflict
- [ ] 5.3 Enforce that requesting changes requires either at least one open comment or a
  non-empty summary note
- [ ] 5.4 Implement the document state query returning latest version, status, and
  unresolved comments with references, ranges, quoted source, and bodies
- [ ] 5.5 Add `POST /api/documents/{slug}/versions/{n}/decision`
- [ ] 5.6 Add Approve and Request changes controls to the document page, with the
  summary note field, and reflect the recorded decision after submission
- [ ] 5.7 Build the index page listing documents, distinguishing pending from decided,
  showing title, project path, and version, each linking to its review page
- [ ] 5.8 Tests: approve sets status and timestamp; request-changes with comments
  succeeds; request-changes with neither comments nor note is rejected; approval with no
  comments succeeds; second decision conflicts; index separates pending from decided;
  pending filter; state query for unknown slug is not found
- [ ] 5.9 Verify by hand: approve one document and request changes on another, then
  confirm the index reflects both

## 6. Agent-facing CLI

- [ ] 6.1 Implement the `review` command: fetch document state and map status to exit
  codes 0, 2, 3, and 4 per design D6
- [ ] 6.2 Implement the LLM-shaped renderer: header line with status, version, and
  unresolved count, then each comment as reference, line range, quoted source, and body
- [ ] 6.3 Make the pending case state explicitly that no decision has been recorded
- [ ] 6.4 Add `--json` to `review`, preserving the exit code
- [ ] 6.5 Implement the `resolve` command taking one or more references and reporting the
  remaining unresolved count
- [ ] 6.6 Implement `list --pending` and `status`
- [ ] 6.7 Ensure exit code 5 is reserved for an unreachable API and never overlaps a
  review outcome
- [ ] 6.8 Add a `--version` flag, and warn when the running server's version differs
  from the CLI's
- [ ] 6.9 Tests: exit code per status; JSON output preserves exit codes; header line
  contents; quoted source present per comment; resolve reports remaining count; exit 5
  when the API cannot be started
- [ ] 6.10 Verify by hand: run the full loop — submit, comment, request changes, `review`
  and confirm exit 2, resolve, resubmit, approve, `review` and confirm exit 0

## 7. Agent skill and documentation

- [ ] 7.1 Write the `md-review` skill with a description that triggers on producing a
  plan or design document for human review
- [ ] 7.2 Document the submit-and-stop step: submit, report the URL, stop without
  implementing
- [ ] 7.3 Document reading the outcome on resume, running `review` first and branching on
  the exit code, with an explicit action for each of 0, 2, 3, and 4, forbidding
  proceeding on 3
- [ ] 7.4 Document the revision loop: address comments, resolve those addressed,
  resubmit for a further round
- [ ] 7.5 Expand the README: what the tool is, install and run instructions, the CLI
  surface with exit codes, skill installation path, and an AGENTS.md snippet
- [ ] 7.6 Add an end-to-end test driving the whole loop through the CLI against a live
  server
- [ ] 7.7 Verify by hand: install the skill, have an agent submit a plan, review it in
  the browser, and confirm the agent picks up the decision on nudge
