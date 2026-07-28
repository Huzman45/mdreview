## Context

The skill is the only thing standing between a working tool and an agent that does
not know it exists. It drifted: five features shipped and none reached it, so an
agent following it writes plainer documents than the renderer can show and cannot
answer "where do I comment on this line?".

## Goals / Non-Goals

**Goals:**

- Bring the skill level with what the tool does.
- Make agents write documents the renderer can display well.
- Make installation reproducible so the skill cannot silently go stale again.
- Keep one source of truth across two agent runtimes.

**Non-Goals:**

- Changing the review protocol, the exit codes, or any source behaviour.
- Editing the operator's personal global agent instructions.
- Any MCP surface.

## Decisions

### D1. The skill teaches authoring, not just protocol

The original skill only described the loop: submit, stop, read the outcome. It now
also states what the renderer supports, because an agent that does not know task
lists and diagrams render will write neither, and the reviewer never sees a feature
that already works.

This is the cheapest available improvement to the *quality of plans* rather than to
the tool.

### D2. One canonical copy, symlinked

The skill lives at `~/.agents/skills/md-review`, with `~/.claude/skills/md-review` a
symlink to it. Two real copies would drift, and the drift would be silent — exactly
the failure this change is fixing.

opencode and Claude Code both resolve the skill through those locations, so no
per-runtime variant is needed.

### D3. Installation is a task, not prose

`mise run setup` installs the CLI and the skill. Prose instructions are easy to
follow half-way, and there was no way to refresh an edited skill short of
remembering the copy and the symlink. The task removes the skill directory before
copying, so a renamed or deleted file cannot survive as a leftover.

### D4. The editable install is kept, and its cost stated

`uv tool install --editable` binds the command to the checkout, so the tool breaks if
the directory moves. That is the right default while the project is under active
development — changes take effect immediately — but it is a real failure mode, so the
README states it and gives the non-editable alternative rather than leaving it to be
discovered.

### D5. Global agent instructions are left alone

The README offers a snippet for the operator's global instructions but the change does
not install it. Making every agent in every project route plans through this tool is a
behavioural decision that belongs to the operator, not to a setup script.

## Risks / Trade-offs

- **The skill drifts again after the next feature.** → `mise run install-skill` makes
  refreshing trivial, and the spec now requires re-running setup to update a stale
  skill. The underlying risk is unchanged: nothing enforces that a feature PR touches
  the skill.
- **Agents overuse diagrams because the skill mentions them.** → The skill says "where
  they fit" rather than encouraging them unconditionally.
- **A symlink confuses a tool that copies rather than follows links.** → Both target
  runtimes read through it; if one ever does not, it degrades to the skill simply not
  being found rather than to a stale copy being used.

## Migration Plan

No data or schema change. Re-running `mise run setup` replaces the installed skill.
Rollback is reinstalling the previous skill file; nothing else is affected.

## Open Questions

Whether the repository should fail its own checks when a feature changes behaviour the
skill describes without touching the skill. That would prevent this class of drift, but
needs a way to express which features the skill covers.
