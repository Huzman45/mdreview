## ADDED Requirements

### Requirement: The review server can run as a supervised service
The system SHALL be installable as a background service so the review server is
available without a terminal session holding it open.

#### Scenario: Installing starts the service
- **WHEN** the operator installs the service
- **THEN** the review server is listening on a discovered private address
- **AND** it is configured to start again after logout or reboot

#### Scenario: The service is restarted if it exits unexpectedly
- **WHEN** the running server process exits without being asked to
- **THEN** the supervisor starts it again

#### Scenario: The address is resolved each time the service starts
- **WHEN** the service starts
- **THEN** it resolves the current private address rather than reusing one recorded
  at install time, so a changed DHCP lease is picked up on restart

### Requirement: The service supervises only the review server
The service definition SHALL reference only the review server. It MUST NOT stop,
start, or otherwise act on any other process or application.

#### Scenario: Only the review server is managed
- **WHEN** the installed service definition is inspected
- **THEN** the only program it runs is the review server's own launcher

#### Scenario: Removal affects nothing else
- **WHEN** the service is removed
- **THEN** no other background service or application is stopped or altered

### Requirement: The service can be removed completely
Installation SHALL be reversible, because a service that cannot be cleanly removed
is a liability.

#### Scenario: Removal stops the server
- **WHEN** the operator removes the service
- **THEN** the server stops listening

#### Scenario: Removal prevents restarting
- **WHEN** the service has been removed
- **THEN** it does not start again by itself, including after a reboot

#### Scenario: Removal is safe when nothing is installed
- **WHEN** removal runs and no service is installed
- **THEN** it succeeds without error

### Requirement: Service state and output are inspectable
The operator SHALL be able to see whether the service is running and read its
output, because a background service that fails silently is worse than none.

#### Scenario: State is reported
- **WHEN** the operator asks for service status
- **THEN** whether it is installed and running is reported, with the address it is
  bound to when running

#### Scenario: Output is written to a known location
- **WHEN** the service runs
- **THEN** its standard output and errors are written to files under the operator's
  log directory

#### Scenario: A failure to start is discoverable
- **WHEN** the service fails to start
- **THEN** the reason is present in its log output rather than being discarded

### Requirement: The service does not weaken access control
Running continuously SHALL NOT reduce the protection applied to LAN requests.

#### Scenario: The token is still required
- **WHEN** the service is running and a request arrives from another machine without
  the token
- **THEN** it is refused exactly as for a manually started server

#### Scenario: Revocation still works
- **WHEN** the token is rotated while the service is running
- **THEN** previously authorised devices are refused
