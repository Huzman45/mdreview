## ADDED Requirements

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
