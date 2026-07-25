## Context

Loopback-only was the correct default for an unauthenticated local tool, but it
also prevents the primary reviewer from opening a plan on their phone. The two
devices already share a private network; the missing capability is a narrow,
explicit way to listen on that network without silently broadening exposure.

## Goals / Non-Goals

**Goals:**

- Make the current reviews reachable at one known private IP.
- Preserve loopback-only behavior unless the operator explicitly opts in.
- Make the security trade-off visible in both the command and startup output.
- Keep lazy autostart working when LAN mode is selected.

**Non-Goals:**

- Authentication, encryption, public exposure, automatic IP discovery, or
  binding every interface.

## Decisions

### One concrete private IP, never a wildcard

`--allow-lan` changes validation from "loopback only" to "loopback or one
concrete private IP." It does not mean "anything goes": `0.0.0.0`, `::`, public
addresses, and hostnames stay invalid.

The alternative was binding `0.0.0.0` for convenience. Rejected because that
also exposes the service on Wi-Fi, VPN interfaces, and interfaces connected
later. Selecting `10.31.41.35` exposes only the intended USB LAN interface.

### Carry the opt-in in Settings

`Settings.allow_lan` is passed through CLI configuration and into the detached
autostart command. `server.run()` revalidates it immediately before opening the
socket, so constructing `Settings` directly cannot bypass the gate.

### Environment equivalent

`MDREVIEW_ALLOW_LAN=1` mirrors the CLI flag. This is needed for agent commands
that should keep returning LAN URLs without repeating flags in every invocation.

### Local API traffic bypasses environment proxies

The CLI HTTP client sets `trust_env=False`. Its only valid targets are loopback
or a private IP accepted by the binding gate, so routing through `HTTP_PROXY` is
never useful. Without this, a corporate proxy can make readiness checks time out
while uvicorn is already listening successfully on the LAN interface.

## Risks / Trade-offs

- **Anyone on the selected network can read and mutate reviews.** → Explicit
  flag, startup warning, private-address restriction, and documentation to stop
  the server when finished. Authentication remains a separate feature.
- **The interface address changes.** → Startup fails visibly; the operator picks
  the current address rather than the tool guessing among several interfaces.
- **Network client isolation blocks the phone anyway.** → The server can verify
  its local bind, but only a request from the phone can prove end-to-end routing.

## Migration Plan

No data migration. Existing commands and loopback startup are unchanged. Stop
the loopback process, install the updated CLI, then start with:

```bash
mdreview serve --host 10.31.41.35 --allow-lan
```

Rollback is stopping that process and starting `mdreview serve` normally.

## Open Questions

Whether LAN access should eventually use a random bearer token. This increment
deliberately keeps authentication out of scope to provide immediate phone access.
