## Why

LAN access works but has to be started by hand and dies with the terminal that
started it, so reviewing from a tablet means going back to the laptop first —
which defeats the point. It also requires typing the current address, and that
address moves: the Wi-Fi address changed three times in one day during
development, and the ethernet address moved from `.35` to `.9`.

The reviewer's tablet reaches the `10.x` ethernet address reliably, including over
their VPN, so no change to which addresses are permitted is needed. What is needed
is for the server to find that address itself and to keep running.

## What Changes

- `--host auto` resolves the machine's own private LAN address at startup instead
  of requiring it to be typed, preferring the address range the operator names.
  A new `lan-address` command prints what it would choose.
- A supervised background service keeps the LAN server running across logout,
  reboot, and crashes, installed and removed by task rather than by editing
  system files.
- Service state is inspectable, and its output is logged to a known location,
  because a background service that fails silently is worse than none.
- **No change to which addresses may be bound.** Wildcard and public addresses
  remain refused, and LAN access still requires the capability token.

## Capabilities

### New Capabilities

- `lan-address-discovery`: choosing the machine's own private LAN address, so a
  changing DHCP lease does not require the operator to look up and retype it.
- `background-service`: running the review server as a supervised background
  service, including installation, removal, and state inspection.

### Modified Capabilities

- `private-lan-access`: the host may be given as `auto`, resolved to a concrete
  private address at startup. The set of permissible addresses is unchanged.

## Non-goals

- **Relaxing the address rules.** Wildcard binding stays refused. The operator
  confirmed the single `10.x` address is reachable from their tablet directly and
  over VPN, so the reason to consider wildcard has gone.
- **Removing or weakening the token.** An always-running service makes the token
  more important, not less.
- **Exposure beyond the local network.** No tunnel, no port forwarding, no TLS.
- **Supervising anything other than the review server.** The service manages one
  process and must never act on another application.
- **Reacting to a DHCP change while running.** The address is resolved at startup;
  a change requires a restart.
- **Cross-platform service support.** macOS only, matching the rest of the tool.

## Impact

- New address-resolution logic, and a `--host auto` value accepted anywhere a host
  is accepted.
- New service definition, a wrapper that resolves the address at start, and tasks
  to install, remove, and report on it.
- Logs under the user's log directory.
- Once installed, the server is running whenever the operator is logged in, so
  rotating the token becomes the way to revoke tablet access rather than stopping
  the server.
