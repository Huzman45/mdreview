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

### Requirement: Supporting commands for operating the loop
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

### Requirement: Several files submit as one document
The CLI SHALL accept several paths to `submit` and assemble them into one
reviewable document: each file contributes a `# <path>` heading — the path
exactly as written by the caller — followed by its content, in argument
order. The assembly SHALL be byte-for-byte deterministic for the same files
and order. A single path SHALL behave exactly as before.

#### Scenario: Files assemble in argument order under path headings
- **WHEN** `submit a.md specs/b.md` is run
- **THEN** one document is recorded whose content opens with `# a.md`,
  followed by that file's content, then `# specs/b.md` and its content

#### Scenario: Assembly is deterministic
- **WHEN** the same files are submitted twice in the same order with no edits,
  the second time against the first submission's slug
- **THEN** the assembled content is byte-identical
- **AND** the still-pending round is reused rather than superseded

#### Scenario: Defaults derive from the common parent directory
- **WHEN** several files are submitted with no `--slug` and no `--title`
- **THEN** both default from the files' deepest common parent directory name

#### Scenario: One file keeps its existing behaviour
- **WHEN** `submit` is run with exactly one path and no options
- **THEN** the submission is identical to today's, with no path heading added

#### Scenario: A missing file fails the whole submission
- **WHEN** any of the given paths does not exist
- **THEN** the command fails naming that path
- **AND** nothing is recorded

### Requirement: Comments report their source file
When a document's content contains two or more assembly headings (a line of
the form `# <path>` with a single-token path), `review` and `await` reports
SHALL annotate each comment with the file and file-local line the comment
range falls in, derived by splitting the content at those headings. Reports
SHALL degrade to their unannotated form when the content cannot be fetched
or contains fewer than two assembly headings.

#### Scenario: A comment maps to its source file and line
- **GIVEN** a document assembled from several files
- **WHEN** a decided review's report includes a comment anchored inside one
  of the files
- **THEN** the comment's label names that file and the line within it

#### Scenario: A comment on a file heading names the file
- **WHEN** a comment anchors on an assembly heading line itself
- **THEN** the label names the file and states it refers to the file heading

#### Scenario: An ordinary document reports as before
- **GIVEN** a document with no assembly headings
- **WHEN** its report is rendered
- **THEN** comment labels carry only the document line range

#### Scenario: An unreachable content endpoint degrades quietly
- **GIVEN** a server that does not expose version content
- **WHEN** a report is rendered
- **THEN** it is the unannotated report, with no error

### Requirement: A version's content is retrievable
The API SHALL serve the stored markdown of any version as plain text, so a
client can re-read exactly what was submitted.

#### Scenario: Stored content round-trips
- **WHEN** `GET /api/documents/{slug}/versions/{n}/content` is requested for
  an existing version
- **THEN** the response is that version's markdown, byte-identical, as
  `text/plain`

#### Scenario: A missing version is a plain 404
- **WHEN** the slug or version does not exist
- **THEN** the response is 404

