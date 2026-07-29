# review-decisions Specification

## Purpose
Recording an approve or request-changes decision against a version, and
exposing the pending or decided state of every document.
## Requirements
### Requirement: A reviewer records one decision per version
A version SHALL carry exactly one review decision. Recording a decision closes that
review round; a further round requires a new version.

#### Scenario: Approving a version
- **GIVEN** a version whose status is `pending`
- **WHEN** the reviewer approves it
- **THEN** its status becomes `approved`
- **AND** the time of the decision is recorded

#### Scenario: Requesting changes on a version
- **GIVEN** a version whose status is `pending` with at least one `open` comment
- **WHEN** the reviewer requests changes
- **THEN** its status becomes `changes_requested`
- **AND** the time of the decision is recorded

#### Scenario: An optional note accompanies the decision
- **WHEN** the reviewer records a decision with a summary note
- **THEN** the note is stored on the version and returned with its status

#### Scenario: A decided version cannot be decided again
- **GIVEN** a version whose status is `approved`
- **WHEN** any decision is submitted for that version
- **THEN** the request is rejected as a conflict
- **AND** the recorded decision is unchanged

### Requirement: Requesting changes requires actionable feedback
Because the agent's next step is driven entirely by comments, requesting changes with
no feedback SHALL be refused rather than producing a revision request the agent cannot
act on.

#### Scenario: Changes cannot be requested without comments
- **GIVEN** a `pending` version with no `open` comments
- **WHEN** the reviewer requests changes without a summary note
- **THEN** the request is rejected with an explanatory error
- **AND** the status remains `pending`

#### Scenario: A summary note alone is sufficient feedback
- **GIVEN** a `pending` version with no `open` comments
- **WHEN** the reviewer requests changes with a non-empty summary note
- **THEN** the status becomes `changes_requested`

#### Scenario: Approval needs no comments
- **GIVEN** a `pending` version with no comments at all
- **WHEN** the reviewer approves it
- **THEN** the status becomes `approved`

### Requirement: Pending reviews are discoverable
The system SHALL expose which active documents are awaiting a decision, so that
a reviewer with several agents in flight can find them without hunting for
URLs. Archived documents are not awaiting anything and stay out of these
listings. Decided documents are history and are presented grouped by day, so
the recent past can be scanned without reading timestamps.

#### Scenario: Index lists documents awaiting review
- **GIVEN** three documents, two of which have a `pending` latest version
- **WHEN** the reviewer opens the index
- **THEN** the two pending documents are listed with their title, project path, and
  version number
- **AND** each links to its review page

#### Scenario: Decided documents are distinguishable
- **WHEN** the reviewer opens the index
- **THEN** documents whose latest version has been decided show that decision rather
  than appearing as awaiting review

#### Scenario: Decided documents are grouped by day
- **GIVEN** decided documents whose latest versions arrived on different days
- **WHEN** the reviewer opens the index
- **THEN** the decided documents appear under one heading per calendar day,
  most recent day first
- **AND** the current day is labelled Today and the previous one Yesterday

#### Scenario: The waiting queue is not sliced by day
- **GIVEN** documents awaiting review submitted on different days
- **WHEN** the reviewer opens the index
- **THEN** they are listed as one queue, newest first, with no day headings

#### Scenario: Pending list can be filtered
- **WHEN** the list of documents is requested restricted to pending reviews
- **THEN** only active documents whose latest version is `pending` are returned

#### Scenario: Archived documents are absent from the index
- **GIVEN** an archived document
- **WHEN** the reviewer opens the index
- **THEN** it is not listed among waiting or decided documents

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

