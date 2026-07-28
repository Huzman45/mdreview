## Why

The skill was written when the review page rendered plain prose and comments could
only target whole blocks. Since then it gained task list checkboxes, diagrams, a
source view for line-precise comments, a diff view, and a token-guarded LAN mode.
An agent following the current skill knows about none of it, so it writes plainer
documents than the renderer can display and cannot tell the user where to look for
the features they asked for.

Installation is also still a sequence of copy and symlink commands documented in
prose, which is easy to get half-right and leaves the skill silently stale after an
edit.

## What Changes

- The skill tells agents which markdown constructs the renderer supports, so plans
  can use task lists and diagrams rather than degrading to plain text.
- The skill describes the rendered, source, and changes views, so an agent can point
  the user at the right one.
- The skill notes that a comment may target a single line, including one inside a
  fenced block, so an agent reads the line range rather than assuming a whole block.
- The skill covers reviewing from another device, including that the address changes
  with DHCP.
- Installing the CLI and the skill becomes one command that also keeps the Claude
  Code and opencode locations in sync from a single source of truth.

## Capabilities

### Modified Capabilities

- `agent-skill`: the skill additionally teaches agents what the renderer can display
  and which views exist, and installation is a single reproducible command rather
  than a documented sequence.

## Non-goals

- **Changing the review protocol.** Submit-and-stop, the exit codes, and the
  revision loop are unchanged.
- **Editing the operator's global agent instructions.** The project documents a
  snippet; whether to adopt it is the operator's decision, since it changes how
  every agent behaves in every project.
- **Supporting agents beyond a skill file and a CLI.** No MCP server.

## Impact

- The skill file and its installation path. No source behaviour changes.
- A `mise` task replaces the documented copy-and-symlink sequence.
- Agents following the refreshed skill will produce plan documents containing task
  lists and diagrams, which the renderer already supports.
