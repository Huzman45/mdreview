## MODIFIED Requirements

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
