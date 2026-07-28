## ADDED Requirements

### Requirement: The machine's own LAN address can be discovered
The system SHALL be able to determine a private address belonging to this machine,
so that a host does not have to be looked up and typed when the DHCP lease moves.

#### Scenario: A private address is chosen
- **WHEN** discovery runs on a machine with a private address on a network interface
- **THEN** that address is returned

#### Scenario: A preferred range wins
- **GIVEN** the machine has addresses in more than one private range
- **WHEN** discovery runs with a preferred range configured
- **THEN** an address from the preferred range is chosen over the others

#### Scenario: Loopback is never chosen
- **WHEN** discovery runs
- **THEN** a loopback address is not returned, because binding it would leave the
  service unreachable from another device

#### Scenario: Public addresses are never chosen
- **WHEN** an interface carries a public address
- **THEN** that address is not returned

#### Scenario: No private address is reported clearly
- **WHEN** discovery runs on a machine with no private address
- **THEN** it fails with a message saying no private address was found, rather than
  returning a placeholder

### Requirement: The chosen address is inspectable
The operator SHALL be able to see which address would be chosen without starting a
server, so a connection problem can be diagnosed separately from the service.

#### Scenario: The address is printed
- **WHEN** the operator asks for the LAN address
- **THEN** the address that would be bound is printed

#### Scenario: Failure to find one is reported
- **WHEN** no private address exists and the operator asks for it
- **THEN** the command fails with a non-zero status and an explanatory message

### Requirement: A host of `auto` resolves at startup
Serving SHALL accept `auto` in place of an address, resolving it when the server
starts.

#### Scenario: Auto resolves to a private address
- **WHEN** the server is started with a host of `auto` and LAN access permitted
- **THEN** it binds a discovered private address
- **AND** the address it bound is reported

#### Scenario: Auto still requires the LAN opt-in
- **WHEN** the server is started with a host of `auto` and no LAN opt-in
- **THEN** startup fails, exactly as it would for a private address typed by hand

#### Scenario: Auto does not widen what may be bound
- **WHEN** a host of `auto` is resolved
- **THEN** the resolved address is subject to the same rules as a typed one, so a
  wildcard or public address can never result
