## Context

Both agent tools run shell commands as child processes and pass environment
down. Investigated on this machine (Claude Code 2.1.220, opencode 1.18.5),
with three local projects as prior art (`session-migrator`, `ocdashboard`,
`retitle`):

- Claude Code exports `CLAUDECODE=1` and `CLAUDE_CODE_SESSION_ID=<uuid>` to
  every Bash-tool child. Some spawn paths deliberately scrub the id while
  keeping other markers, so a missing id must read as "unknown", not "not
  Claude Code".
- opencode exports `OPENCODE=1` and `OPENCODE_PID` but **no session id**. Its
  plugin API fires a `shell.env` hook per shell command with
  `{cwd, sessionID, callID}` and merges the returned env into that command.
- Session id formats are distinctive: `ses_` + 26 chars (opencode) versus a
  UUID (Claude Code), so a bare id's tool is inferable.

## Goals / Non-Goals

**Goals:** capture tool + session automatically at submit time; degrade to
tool-only when the id is unavailable; show it where the reviewer looks.

**Non-Goals:** titles; process-tree inspection; reading either tool's
session stores at render time.

## Decisions

### D1. Environment variables only, read at submit time

The alternatives — walking the process tree to a registered pid, or matching
cwd against the newest session in opencode's database — are documented in the
prior art as ambiguous under concurrency (several live sessions share a
working directory on this machine right now) and stale under write-lag. Env
vars are set by the session that actually ran the command. They are read when
`submit` executes, not at import: Claude Code rewrites its session id in
place after a conversation reset.

### D2. Precedence: explicit, then proximate, then inherited, then presence

`MDREVIEW_SESSION_ID` first — an explicit override must always win, and it is
the pre-existing contract. Then `OPENCODE_SESSION_ID`: it is injected
per-command by the plugin hook, so when present it names the session that ran
this very command. Then `CLAUDE_CODE_SESSION_ID`, which is inherited through
arbitrary descendants — real but less proximate (an opencode session started
from inside a Claude Code shell carries both; the opencode one issued the
command). Last, the presence markers `OPENCODE=1` / `CLAUDECODE=1` give
tool-only provenance when every id was scrubbed or the plugin is absent.

### D3. A plugin for opencode rather than a heuristic

opencode's `shell.env` hook exists precisely to inject per-command
environment and is handed the session id. Ten declarative lines
(`contrib/opencode/mdreview-session.js`, installed to
`~/.config/opencode/plugins/` by `mise run setup`) beat any read of
`opencode.db`: no lock contention, no write-lag window, no
newest-session-for-cwd guess. Without the plugin, opencode submissions still
record the tool.

### D4. `session_tool` is a stored column, not a display inference

The tool is inferable from the id format today, but tool-only provenance (id
scrubbed, plugin missing) has no id to infer from, and a stored fact
outlives format coincidences. Migration step 4 adds the column and backfills
it from the two known id shapes where an id already exists.

### D5. Shown as provenance, not decoration

The colophon — the page's metadata line — gains "Claude Code session
1e0e56a0" (full id on hover). The index row's sub-line appends the tool name
after the project path, nothing more: at index granularity "which tool" is
scannable, "which session" is noise. The API document response carries both
fields for anything that wants to build on them.

## Risks / Trade-offs

- **The plugin is another installed artifact.** Mitigated: same one-command
  setup as the skill, and its absence degrades to tool-only capture rather
  than breaking anything.
- **Nested sessions attribute to the inner tool** (D2). That is the intended
  reading of "which conversation do I go back to".
- **Env leakage in tests.** The suite itself runs inside an agent session,
  so tests that exercise detection must pin these variables explicitly or
  they inherit the session running the tests.
