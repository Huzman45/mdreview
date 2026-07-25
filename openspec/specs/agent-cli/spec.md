# agent-cli Specification

## Purpose
The `mdreview` command surface used by an agent: its exit-code contract
and the LLM-oriented rendering of review outcomes and comments.

## Requirements
### Requirement: Submitting a document from the command line
The CLI SHALL publish a local markdown file for review and report where to review it,
without blocking on the reviewer.

#### Scenario: File is submitted and its URL reported
- **WHEN** `submit` is run against an existing markdown file
- **THEN** the file's content is recorded as a version
- **AND** the review page URL is printed
- **AND** the command exits 0 immediately

#### Scenario: Browser is opened by default
- **WHEN** `submit` is run without opt-out
- **THEN** the review page is opened in the default browser

#### Scenario: Browser opening can be suppressed
- **WHEN** `submit` is run with the no-open flag
- **THEN** no browser is launched
- **AND** the URL is still printed

#### Scenario: Missing file fails clearly
- **WHEN** `submit` is run against a path that does not exist
- **THEN** the command fails with a message naming the path
- **AND** nothing is recorded

#### Scenario: Provenance is sent automatically
- **WHEN** `submit` is run inside a project directory
- **THEN** the working directory is recorded as the document's project path without
  the caller specifying it

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
- **AND** the unresolved comments are printed

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
- **WHEN** `review` prints an unresolved comment
- **THEN** the output includes the comment's reference, its line range, the quoted
  markdown source of the anchored block, and the comment body

#### Scenario: A summary header precedes the comments
- **WHEN** `review` prints its result
- **THEN** the first line reports the review status, the version number, and the count
  of unresolved comments

#### Scenario: Machine-readable output is available
- **WHEN** `review` is run with the JSON flag
- **THEN** the output is a single JSON object containing the status, version, and
  comments
- **AND** the exit code is unchanged from the human-readable form

### Requirement: Supporting commands for the review loop
The CLI SHALL provide the operations needed to run the loop without opening a browser
or writing HTTP requests by hand.

#### Scenario: Resolving comments by reference
- **WHEN** `resolve` is run with one or more comment references for a document
- **THEN** each named comment becomes `resolved`
- **AND** the count of remaining unresolved comments is reported

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

### Requirement: The CLI tolerates a stopped server
Because there is no daemon, every command that needs the API SHALL be responsible for
making it available.

#### Scenario: Command succeeds with no server running
- **GIVEN** no server is listening on the configured port
- **WHEN** any command that needs the API is run
- **THEN** a server is started automatically
- **AND** the command completes successfully

#### Scenario: Unreachable server is reported distinctly
- **WHEN** the API cannot be reached and cannot be started
- **THEN** the command exits 5
- **AND** the message distinguishes this from a review outcome

