## MODIFIED Requirements

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

#### Scenario: The agent session is detected automatically
- **WHEN** `submit` is run from a shell command inside an agent session that
  exposes its identity to child processes
- **THEN** the session tool and identifier are recorded on the document
  without the caller specifying them

#### Scenario: An explicit session identifier wins
- **WHEN** `submit` is run with `MDREVIEW_SESSION_ID` set
- **THEN** that identifier is recorded regardless of any detected session

#### Scenario: A session tool without an identifier is still recorded
- **WHEN** `submit` is run inside an agent session that marks its presence
  but exposes no identifier
- **THEN** the tool is recorded and the identifier is left empty
