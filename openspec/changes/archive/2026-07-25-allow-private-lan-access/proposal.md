## Why

The loopback-only default makes reviews inaccessible from a phone, even when the
phone and development machine share a private network. A reviewer should be able
to opt into that access without turning an unauthenticated local tool into a
service listening on every interface.

## What Changes

- Add an explicit `--allow-lan` opt-in for binding to one concrete private IP.
- Keep loopback as the default and continue rejecting LAN binds without opt-in.
- Continue rejecting wildcard, public, and hostname binds even after opt-in.
- Propagate the opt-in through lazy autostart and all CLI commands.
- Warn whenever the server is exposing unauthenticated reviews on a LAN.
- Document the equivalent `MDREVIEW_ALLOW_LAN=1` environment setting.

## Capabilities

### New Capabilities

- `private-lan-access`: Explicit, constrained access to the review server from a
  device on the same private network.

### Modified Capabilities

None. The original capabilities have not yet been archived into the canonical
spec store, so this increment is expressed as a separate capability.

## Non-goals

- Authentication or per-review access tokens.
- Public internet exposure.
- Wildcard binding to all local interfaces.
- Automatic interface or IP selection.

## Impact

- Network binding validation in `config.py` and `server.py`.
- A new option on the CLI and its autostart subprocess command.
- Anyone who can route to the selected private address can read and mutate review
  state while the server is running; the warning and explicit gate make this
  trade-off visible.
