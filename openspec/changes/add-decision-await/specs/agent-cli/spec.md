## ADDED Requirements

### Requirement: The outcome can be awaited without holding a turn
The CLI SHALL provide an `await` command that runs until the document's
latest version is decided and then exits with the same code and report as
`review`, so a harness that runs background tasks can deliver the outcome to
an agent without the human relaying it. Awaiting is a client-side poll; the
server holds no connection and needs no new state.

#### Scenario: A decision ends the wait with its outcome
- **GIVEN** an `await` running against a pending document
- **WHEN** the reviewer approves the latest version
- **THEN** the command exits 0
- **AND** its output is the same report `review` would print

#### Scenario: Requested changes end the wait with the feedback
- **GIVEN** an `await` running against a pending document
- **WHEN** the reviewer requests changes
- **THEN** the command exits 2
- **AND** the open comments are printed

#### Scenario: An already-decided document returns immediately
- **GIVEN** a document whose latest version is already decided
- **WHEN** `await` is run for it
- **THEN** it exits at once with that outcome's code

#### Scenario: The wait is bounded
- **WHEN** `await` runs past its timeout with no decision recorded
- **THEN** it exits 3
- **AND** the output states that no decision has been recorded

#### Scenario: An unreachable server is not an outcome
- **GIVEN** a server that cannot be reached and cannot be started
- **WHEN** `await` runs for it
- **THEN** the command exits 5 rather than reporting any review outcome
