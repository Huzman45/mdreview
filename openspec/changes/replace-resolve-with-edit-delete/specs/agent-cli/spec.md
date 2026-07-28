## MODIFIED Requirements

### Requirement: Exit codes communicate the review outcome
The `review` command SHALL signal the outcome through its exit status, so an agent can
branch on the result without parsing text and cannot mistake an undecided review for
an approval.

#### Scenario: Approved review exits zero
- **GIVEN** a document whose latest version is `approved`
- **WHEN** `review` is run for it
- **THEN** the command exits 0

#### Scenario: Requested changes exit two
- **GIVEN** a document whose latest version is `changes_requested`
- **WHEN** `review` is run for it
- **THEN** the command exits 2
- **AND** the open comments are printed

#### Scenario: Undecided review exits three
- **GIVEN** a document whose latest version is `pending`
- **WHEN** `review` is run for it
- **THEN** the command exits 3
- **AND** the output states that no decision has been recorded yet

#### Scenario: Cancelled review exits four
- **GIVEN** a document whose latest version has been cancelled
- **WHEN** `review` is run for it
- **THEN** the command exits 4

### Requirement: Comment output is shaped for a language model
The `review` command SHALL render feedback so that an agent can act on it without
re-reading the document.

#### Scenario: Each comment quotes the source it refers to
- **WHEN** `review` prints an open comment
- **THEN** the output includes the comment's reference, its line range, the quoted
  markdown source of the anchored block, and the comment body

#### Scenario: A summary header precedes the comments
- **WHEN** `review` prints its result
- **THEN** the first line reports the review status, the version number, and the count
  of open comments

#### Scenario: Requested changes instruct resubmission
- **WHEN** `review` reports `changes_requested`
- **THEN** the output instructs the agent to address each comment and resubmit the
  revised file under the same slug
- **AND** no step requires the agent to mark comments as addressed

#### Scenario: Machine-readable output is available
- **WHEN** `review` is run with the JSON flag
- **THEN** the output is a single JSON object containing the status, version, and
  comments
- **AND** the exit code is unchanged from the human-readable form

### Requirement: Supporting commands for the review loop
The CLI SHALL provide the operations needed to run the loop without opening a browser
or writing HTTP requests by hand. Comments belong to the reviewer: no CLI command
creates, changes, or removes one.

#### Scenario: Listing documents awaiting review
- **WHEN** `list` is run restricted to pending documents
- **THEN** each pending document is printed with its slug, title, version, and project
  path

#### Scenario: Serving in the foreground
- **WHEN** `serve` is run in foreground mode
- **THEN** the server runs attached to the terminal until interrupted

#### Scenario: Opening a review page
- **WHEN** `open` is run for an existing document
- **THEN** its review page is opened in the default browser
