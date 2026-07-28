# private-lan-access Specification

## Purpose
Explicit, constrained, token-guarded access to the review server from another
device on the same private network. Narrows the default established by
`server-runtime`. Loopback is never subject to the token, so the agent CLI is
unaffected.
## Requirements
### Requirement: LAN access requires explicit consent
The service SHALL continue to bind to loopback by default. Binding to a private
network address MUST require an explicit opt-in so that an ordinary invocation
cannot expose review contents to another machine. The address MAY be given as
`auto`, which is resolved to a concrete private address of this machine before the
opt-in is checked, so that discovery cannot be used to bypass it.

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

#### Scenario: Auto resolves to a private address under the same opt-in
- **WHEN** the server is asked to bind to `auto` with `--allow-lan`
- **THEN** it resolves a private address of this machine and listens on it

#### Scenario: Auto without the opt-in is refused
- **WHEN** the server is asked to bind to `auto` without LAN access enabled
- **THEN** startup fails before a socket is opened

### Requirement: LAN access is constrained to one private interface
The LAN opt-in SHALL permit one concrete private IP only. It MUST NOT permit a
wildcard, public IP, or hostname, because those expose the service more broadly
than intended even though LAN requests must present a token.

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
The CLI SHALL report when the server is listening outside loopback, because anyone who
can reach the selected address and hold the token can read and mutate review state.

#### Scenario: Starting on LAN prints a warning
- **WHEN** the server starts successfully on a private address
- **THEN** stderr states that reviews are exposed on the network
- **AND** it prints the full URL including the token

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

### Requirement: LAN requests must present a capability token
A request arriving from a non-loopback address SHALL be served only if it presents the
current token. Binding to the LAN is what makes the service reachable; the token is what
makes it usable.

#### Scenario: A tokenised LAN request is served
- **WHEN** a request from another machine presents the current token
- **THEN** it is served normally

#### Scenario: An untokenised LAN request is refused
- **WHEN** a request from another machine presents no token
- **THEN** it is refused with an authorisation error
- **AND** the response contains no document titles, slugs, or content

#### Scenario: A wrong token is refused
- **WHEN** a request from another machine presents a token that is not the current one
- **THEN** it is refused with an authorisation error

#### Scenario: Loopback requests need no token
- **WHEN** a request arrives from a loopback address
- **THEN** it is served without a token
- **AND** this holds whether or not LAN access is enabled

#### Scenario: Mutating requests are protected too
- **WHEN** an untokenised request from another machine attempts to create a comment or
  record a decision
- **THEN** it is refused and no state changes

### Requirement: Presenting the token requires no typing
The token SHALL be conveyed in the URL the server prints, and the browser MUST be able
to reuse it for subsequent requests without it appearing in every URL. A token that had
to be transcribed onto a phone would not be used.

#### Scenario: The printed LAN URL carries the token
- **WHEN** the server starts on a private address
- **THEN** the URL it prints includes the token as a query parameter

#### Scenario: The token is remembered for subsequent requests
- **WHEN** a browser opens a tokenised LAN URL
- **THEN** later requests from that browser to the same origin are served without the
  token in the URL

#### Scenario: Loopback URLs stay clean
- **WHEN** the server starts on loopback
- **THEN** the URL it prints carries no token

### Requirement: The token is stored safely and can be rotated
The token SHALL be stored in the data directory with owner-only permissions, SHALL
survive a restart, and MUST be replaceable so that access can be revoked.

#### Scenario: Token is generated on first LAN use
- **WHEN** LAN access is enabled and no token exists
- **THEN** a token with at least 128 bits of entropy is generated and stored in the
  data directory

#### Scenario: Token file is not world-readable
- **WHEN** the token is written
- **THEN** its file permissions allow access to the owner only

#### Scenario: Token is stable across restarts
- **WHEN** the server is restarted with LAN access enabled
- **THEN** the previously issued token is still accepted

#### Scenario: Rotation invalidates the old token
- **WHEN** the token is rotated
- **THEN** the previous token is refused
- **AND** the newly printed URL carries the new token

