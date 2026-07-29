## MODIFIED Requirements

### Requirement: The current state of a document is queryable
The system SHALL report the latest version of a document, its review status, and its
open comments as a single answer, since that is exactly what an agent needs on
resume.

#### Scenario: State of a pending document
- **WHEN** the state of a document whose latest version is undecided is requested
- **THEN** the reported status is `pending`

#### Scenario: State of a document with requested changes
- **GIVEN** a version marked `changes_requested` with two `open` comments
- **WHEN** the state of that document is requested
- **THEN** the reported status is `changes_requested`
- **AND** both comments are returned with their references, line ranges, quoted source,
  and bodies

#### Scenario: Unknown document is reported
- **WHEN** the state of a slug that does not exist is requested
- **THEN** the request fails with a not-found error
