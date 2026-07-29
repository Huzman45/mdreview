## Why

`documents.session_id` has existed since the first schema and has never once
been non-null: the CLI reads `MDREVIEW_SESSION_ID`, which nothing sets. A
reviewer with several agents in flight can see which *project* a document came
from but not which *conversation* — which is the thing they would actually go
back to.

## What Changes

- **Submission detects the originating session by itself.** Claude Code
  already exports `CLAUDE_CODE_SESSION_ID` to every shell command; opencode
  exports only its presence (`OPENCODE=1`), so this change ships a ten-line
  opencode plugin that injects `OPENCODE_SESSION_ID` per command through
  opencode's `shell.env` hook. `MDREVIEW_SESSION_ID` remains as an explicit
  override.
- **The tool is stored beside the id** (`session_tool`: `claude-code` or
  `opencode`), including when the tool is identifiable but the id is not —
  presence markers survive even where ids are scrubbed.
- **The provenance is shown**: the document colophon carries the tool and a
  shortened session id (full id on hover); the index row's sub-line names the
  tool after the project path.
- `mise run setup` installs the opencode plugin along with the CLI and skill.

## Capabilities

### Modified Capabilities

- `document-submission`: provenance covers the session tool; captured
  automatically.
- `agent-cli`: submit detects and sends session identity without flags.
- `agent-skill`: the one-command setup also installs the opencode plugin.
- `markdown-review-page`: the page reports the originating session.

## Non-goals

- **Session titles.** Resolving a human-readable conversation title means
  reading the other tools' stores at render time; the id and tool are stable
  provenance, titles are a separate feature.
- **Grouping the index by session.** Possible once this lands; its own
  decision.
- **Parent-process forensics.** Environment variables cover the real cases;
  walking process trees to catch scrubbed environments is complexity without
  a demonstrated need.

## Impact

- Migration step 4 (`documents.session_tool`, backfilled from stored id
  formats), `models.py`, `store.py`, `api.py`, `cli.py`, a new
  `session.py`, the colophon and docrow templates, `contrib/opencode/`
  plugin, `mise.toml` setup task, README.
