# private-lan-access Specification

## Purpose
Explicit, constrained access to the review server from another device on the
same private network. Narrows the default established by `server-runtime`.

## Requirements
### Requirement: LAN access requires explicit consent
The service SHALL continue to bind to loopback by default. Binding to a private
network address MUST require an explicit opt-in so that an ordinary invocation
cannot expose review contents to another machine.

#### Scenario: Private address without opt-in is refused
- **WHEN** the server is asked to bind to `10.31.41.35` without LAN access enabled
- **THEN** startup fails before a socket is opened
- **AND** the error names `--allow-lan` as the explicit opt-in

#### Scenario: Private address with opt-in is accepted
- **WHEN** the server is asked to bind to `10.31.41.35` with `--allow-lan`
- **THEN** it listens on that address
- **AND** a device able to route to that address can load review pages

#### Scenario: Environment opt-in is equivalent
- **WHEN** `MDREVIEW_ALLOW_LAN=1` and `MDREVIEW_HOST` names a private address
- **THEN** CLI autostart may launch the server on that address

### Requirement: LAN access is constrained to one private interface
The LAN opt-in SHALL permit one concrete private IP only. It MUST NOT permit a
wildcard, public IP, or hostname, because those can expose the unauthenticated
service more broadly than intended.

#### Scenario: Wildcard addresses remain refused
- **WHEN** `0.0.0.0` or `::` is supplied with `--allow-lan`
- **THEN** startup fails and asks for one private LAN address

#### Scenario: Public addresses remain refused
- **WHEN** a public address is supplied with `--allow-lan`
- **THEN** startup fails before opening a socket

#### Scenario: Hostnames remain refused
- **WHEN** a hostname is supplied with `--allow-lan`
- **THEN** startup fails and asks for a concrete private IP

### Requirement: Exposure is visible to the operator
The CLI SHALL warn when the server is listening outside loopback, because anyone
who can reach the selected address can read and mutate review state.

#### Scenario: Starting on LAN prints a warning
- **WHEN** the server starts successfully on a private address
- **THEN** stderr states that unauthenticated reviews are exposed at the full URL

#### Scenario: Loopback startup remains quiet
- **WHEN** the server starts on the default loopback address
- **THEN** no LAN exposure warning is printed

### Requirement: CLI commands can use the LAN server
Every CLI operation that accepts a host SHALL also accept the LAN opt-in and
propagate it to a server started on demand.

#### Scenario: Autostart preserves the opt-in
- **WHEN** a CLI command targets a private address with LAN access enabled and no
  server is running
- **THEN** its detached server command includes `--allow-lan`
- **AND** the original command completes against that server

#### Scenario: Review URLs use the selected private address
- **WHEN** a document is submitted through a server configured at `10.31.41.35`
- **THEN** the returned review URL starts with `http://10.31.41.35:`

