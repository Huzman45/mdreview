## Context

The reviewer wants the review page on a tablet without first going to the laptop.
LAN binding and the capability token already exist, so what is missing is that the
server must find its own address and must keep running.

Review of the proposal corrected an assumption worth recording. I had inferred from
`kyuu.local` resolving to every interface that a tablet might land on the Wi-Fi
address and fail, and proposed relaxing the wildcard prohibition to cover both
networks. The operator's own knowledge overrode that: the `10.x` ethernet address is
reachable from the tablet directly and over their VPN, evidenced by the tablet
already reaching another service on that address. Wildcard is therefore unnecessary,
and this change touches no address rules at all — a smaller and better outcome than
the one I recommended.

## Goals / Non-Goals

**Goals:**

- The server finds its own private address, so a moved DHCP lease costs nothing.
- The server keeps running across logout, reboot, and crashes.
- Installation is reversible, and removal is verifiable.
- Failures are visible rather than silent.

**Non-Goals:**

- Changing which addresses may be bound. Wildcard and public stay refused.
- Weakening or bypassing the token.
- Supervising any process other than the review server.
- Reacting to a DHCP change without a restart.
- Anything beyond macOS.

## Decisions

### D1. Selection is a pure function; enumeration is not

Address discovery splits in two. Enumerating the machine's interfaces is
platform-specific and untestable in a unit test, so it is one small function that
shells out. Choosing among the results is a pure function over a list, which is where
all the rules live: skip loopback, skip public, prefer a named range.

That split means the interesting behaviour — preference order, refusing loopback,
failing when nothing suitable exists — is tested directly, without depending on
whatever interfaces the test machine happens to have.

*Alternative considered:* a dependency such as `psutil` for enumeration. Rejected;
one `ifconfig` call is smaller than a new dependency for a tool that is already
macOS-only in its service layer.

### D2. `auto` resolves before the safety check, never after

`--host auto` is substituted for a concrete address *before* `require_safe_bind`
runs. Discovery is therefore incapable of widening what may be bound: whatever it
returns is validated by exactly the same rule as a typed address, so it cannot
produce a wildcard or a public bind even if enumeration returns something strange.

Getting this order wrong would turn a convenience into a hole, which is why the
spec states it as a requirement rather than leaving it to implementation.

### D3. Preference is configurable, defaulting to the range that works here

Selection prefers `10.` by default because that is the range the operator confirmed
their tablet reaches, and it is overridable by environment variable. Hardcoding an
interface name was rejected: `en7` is a USB adapter and there are eight `utun`
tunnels on this machine, so interface names are far less stable than address ranges.

### D4. launchd, with the narrowest possible definition

The service is a launchd agent with `RunAtLoad` and `KeepAlive`, modelled on the
agent the operator already runs for another tool. It names exactly one program: a
wrapper that resolves the address and executes the server.

The wrapper exists so the address is resolved *at every start* rather than baked in
at install time, which is what makes a changed DHCP lease a restart rather than a
reinstall.

**Constraint, stated because I violated it earlier today:** the definition
references only this tool's own launcher. It does not quit, restart, or signal any
other application. Earlier I submitted a launchd job that repeatedly terminated the
operator's editor, because `launchctl submit` restarts a job that exits and my
script exited by design. The distinction that matters is that a service supervises a
*long-running server*, which is what `KeepAlive` is for, whereas supervising a script
that finishes is a restart loop. This change is the former.

### D5. Removal is a first-class operation, and is tested

`uninstall-service` boots the service out and deletes its definition, and is
idempotent so running it when nothing is installed is not an error. Verification
includes stopping it and confirming it stays stopped, not merely that it starts —
an always-on service that cannot be turned off is a liability.

### D6. Status reads launchd, not a pidfile

Status asks launchd for the service state and reports the bound address. A pidfile
would be a second source of truth that can disagree with reality after a crash.

## Risks / Trade-offs

- **The server is now always exposed on the LAN.** Previously it ran only when
  deliberately started. → The token is required and unchanged, rotation revokes, and
  status makes it easy to see. Called out in the docs rather than implied.
- **A DHCP change breaks it until restart.** → Accepted and documented; the fix is
  restarting the service, which is one task. Watching for address changes was judged
  more machinery than the problem deserves.
- **`KeepAlive` masks a crash loop.** A server that dies immediately will be
  restarted forever. → Output is logged, and status reports state, so the loop is
  discoverable. This is a genuine residual risk of `KeepAlive`.
- **A stale token on the tablet looks like a broken page.** → Unchanged behaviour: a
  403 with an instruction to reopen the printed link.
- **Two servers may run, one on loopback from CLI autostart and one on the LAN.** →
  Already the documented shape; they share the database in WAL mode.

## Migration Plan

No schema or data change. Installing starts the service; removing stops it and
deletes the definition. Existing manual `mdreview serve` usage is unaffected, and
`--host auto` is additive.

Rollback is `uninstall-service`, after which the tool behaves exactly as before.

## Open Questions

Whether the service should watch for address changes and rebind, rather than needing
a restart. Deferred until it proves annoying in practice; the address changed several
times in a day during development, so it may.
