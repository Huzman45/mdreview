## 1. LAN address discovery

- [x] 1.1 Add interface enumeration returning `(interface, address)` pairs for this
  machine, isolated so the rest of the logic needs no real interfaces
- [x] 1.2 Add a pure selection function: skip loopback, skip public, prefer a
  configurable address range, raise a clear error when nothing is suitable
- [x] 1.3 Accept `auto` as a host and resolve it **before** the bind safety check, so
  discovery cannot widen what may be bound
- [x] 1.4 Add a `lan-address` command printing the chosen address, non-zero when none
- [x] 1.5 Report the resolved address when serving with `auto`
- [x] 1.6 Tests: preference order; loopback and public refused; empty input errors;
  `auto` still requires the LAN opt-in; a resolved address is validated by the same
  rule as a typed one

## 2. Background service

- [x] 2.1 Add a launchd agent definition with `RunAtLoad` and `KeepAlive`, naming only
  this tool's own launcher and no other application
- [x] 2.2 Add a wrapper that resolves the address at every start and execs the server,
  so a moved DHCP lease is picked up on restart
- [x] 2.3 Log standard output and errors under the operator's log directory
- [x] 2.4 Add `install-service`, `uninstall-service` and `service-status` tasks
- [x] 2.5 Make removal idempotent and complete: stops the server, deletes the
  definition, and prevents restarting
- [x] 2.6 Report installed and running state plus the bound address, read from launchd
  rather than a pidfile
- [x] 2.7 Tests: the generated definition references only this tool; the wrapper
  resolves rather than hardcodes; log paths are set

## 3. Verification and documentation

- [x] 3.1 Verify install: exactly one LAN listener, correct address, token enforced
- [x] 3.2 Verify removal: server stops, stays stopped, and running removal again is
  not an error
- [x] 3.3 Confirm no other launchd service or application was affected
- [x] 3.4 Confirm reachable from the tablet at the discovered address
- [x] 3.5 Document the service, the always-on exposure, rotation as the way to revoke,
  and that a DHCP change needs a restart
- [x] 3.6 Full suite, lint, format
