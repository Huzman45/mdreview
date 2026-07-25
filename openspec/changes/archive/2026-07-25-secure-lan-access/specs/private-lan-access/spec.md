## ADDED Requirements

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

## MODIFIED Requirements

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
