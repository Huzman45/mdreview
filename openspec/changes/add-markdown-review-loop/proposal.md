## Why

When an AI coding agent writes a plan to a markdown file, reviewing it means opening
an editor, reading raw markdown, and then describing feedback back to the agent in
prose — "change the bit in line 5, and also line 10". Feedback gets detached from the
text it refers to, the agent has to guess which passage you meant, and there is no
record of what was agreed. The review step is the highest-leverage moment in an
agent workflow and it currently has the worst ergonomics of any part of it.

This change builds the missing surface: a local web page where a markdown document
can be read as rendered prose, annotated passage by passage, and explicitly approved
or sent back — with the outcome readable by the agent that asked for it.

## What Changes

- A local HTTP service that stores submitted markdown documents and serves them as
  rendered, annotatable web pages on loopback.
- Submitting a document snapshots it as an **immutable version**. Re-submitting the
  same document creates a new version rather than mutating the old one, so a review
  round and a version are the same thing.
- The review page renders markdown (not raw source) and lets a reviewer attach a
  comment to any individual heading, paragraph, list item, or fenced code block.
- A reviewer records one of two decisions per version: **approve** or **request
  changes**. The decision is what the agent branches on.
- When a revision is submitted, comments on the prior version become `outdated`
  rather than being re-anchored onto shifted line numbers.
- A CLI (`mdreview`) is the sole agent-facing interface. `submit` publishes a
  document and opens the browser; `review` reads back the decision and any
  unresolved comments, quoting the source text each one refers to.
- `review` communicates the outcome through **exit codes** (approved / changes
  requested / still pending / cancelled) so an agent can branch without parsing
  output, and cannot mistake "not yet reviewed" for "approved".
- The CLI starts the server on demand, so there is no daemon to install or manage.
- An `md-review` skill teaches agents the protocol so the loop works without the
  human remembering any commands.

## Capabilities

### New Capabilities

- `server-runtime`: the HTTP service lifecycle — loopback-only binding, SQLite
  storage location, schema migration on startup, and on-demand start from the CLI.
- `document-submission`: accepting a markdown file and recording it as an immutable,
  content-hashed version belonging to a named document.
- `markdown-review-page`: rendering a version as HTML in which every block element
  carries the source line range it came from, so prose can be read and addressed at
  the same time.
- `block-comments`: creating and listing comments anchored to a block's line range
  within a specific version, and the `open` / `resolved` / `outdated` lifecycle those
  comments move through as versions accumulate.
- `review-decisions`: recording an approve or request-changes decision against a
  version, and exposing the pending/decided state of every document.
- `agent-cli`: the `mdreview` command surface, its exit-code contract, and the
  LLM-oriented rendering of decisions and comments.
- `agent-skill`: the packaged instructions that make an agent reach for this tool
  when it produces a plan, and read the result back correctly on resume.

### Modified Capabilities

None. This is the first change in the project.

## Non-goals

- **Authentication and multi-user review.** The service binds to loopback for a
  single operator. No accounts, no permissions, no sharing.
- **Comment anchor relocation.** Comments never migrate across versions. Anchors are
  valid precisely because the version they point into is frozen.
- **Threaded discussion.** A comment is a single note, not a conversation. There is
  no reply chain, no mentions, no notifications.
- **Editing documents in the browser.** The agent owns the file; the reviewer
  comments on it. The page is read-and-annotate only.
- **Realtime collaboration.** No presence, no live cursors, no websockets.
- **Blocking the agent.** The agent submits and stops. The service will never hold a
  connection open waiting for a human.
- **Hosting beyond localhost.** No tunnels, no TLS, no deployment story.

## Impact

- **New codebase.** No existing code is affected; the repository is empty apart from
  bootstrap files.
- **New runtime dependencies:** `fastapi`, `uvicorn`, `jinja2`, `markdown-it-py`,
  `typer`. htmx is vendored as a static asset. No bundler or Node toolchain.
- **New local state:** a SQLite database under the user's data directory. It persists
  across restarts and is the only mutable state the tool owns.
- **New user-facing surface:** a CLI on `PATH` and a web UI on a fixed loopback port.
- **Agent configuration:** a skill installed into the user's skills directory, plus a
  short AGENTS.md snippet, so agents discover the tool.
