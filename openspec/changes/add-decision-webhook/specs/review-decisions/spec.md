## ADDED Requirements

### Requirement: A recorded decision is announced to a configured endpoint
When an endpoint is configured, recording a decision SHALL POST the decision to
it, so that a consumer outside the review loop learns the outcome without
polling for it. Announcing SHALL NOT be able to fail, delay, or alter the
decision it announces: a review tool that refused a decision because a listener
was down would be worse than one that never announced anything.

#### Scenario: A decision is announced
- **GIVEN** a configured endpoint
- **WHEN** the reviewer records a decision on a version
- **THEN** that endpoint receives one request carrying the document slug, the
  version number, the status, the decision note, and the time of the decision

#### Scenario: Both decision surfaces announce
- **GIVEN** a configured endpoint
- **WHEN** a decision is recorded from the review page, and another from the
  API
- **THEN** each is announced once

#### Scenario: A version is announced at most once
- **GIVEN** a version whose decision has been announced
- **WHEN** a further decision is submitted for that version
- **THEN** the request is rejected as a conflict
- **AND** no further announcement is made

#### Scenario: An unreachable endpoint does not affect the decision
- **GIVEN** a configured endpoint that refuses the connection, fails, or never
  answers
- **WHEN** the reviewer records a decision
- **THEN** the decision is recorded and reported as successful
- **AND** the reviewer sees no error and waits no longer than usual

#### Scenario: The announcement follows the recording
- **GIVEN** a configured endpoint
- **WHEN** it receives the announcement and reads the document's state back
- **THEN** the state reports the decision it was told about

#### Scenario: No endpoint configured
- **GIVEN** no configured endpoint
- **WHEN** the reviewer records a decision
- **THEN** no request is sent

### Requirement: The announcement can authenticate to its receiver
A receiver that acts on a decision SHALL be reachable even when it requires its
callers to authenticate. When a token is configured, the announcement SHALL
present it as a bearer credential; when none is configured, the announcement
SHALL carry no authentication and behave exactly as before. A rejected
credential SHALL be treated as any other delivery failure.

#### Scenario: A configured token is presented
- **GIVEN** a configured endpoint and a configured token
- **WHEN** the reviewer records a decision
- **THEN** the request carries that token as a bearer credential in its
  `Authorization` header

#### Scenario: No token configured
- **GIVEN** a configured endpoint and no configured token
- **WHEN** the reviewer records a decision
- **THEN** the request carries no `Authorization` header

#### Scenario: A rejected token does not affect the decision
- **GIVEN** a configured endpoint that rejects the credential
- **WHEN** the reviewer records a decision
- **THEN** the decision is recorded and reported as successful
- **AND** the reviewer sees no error
