## MODIFIED Requirements

### Requirement: A version is served as rendered markdown
The review page SHALL present a version as rendered HTML, not as raw markdown source,
because reading formatted prose is the reason the page exists. Markdown constructs that
carry meaning SHALL be rendered as their semantic equivalents rather than as literal
text, and the page SHALL offer navigation to the other views of the same version.

#### Scenario: Markdown is rendered to HTML
- **WHEN** a reviewer opens the review page for a version
- **THEN** markdown constructs including headings, emphasis, lists, links, tables, and
  fenced code blocks are rendered as their HTML equivalents

#### Scenario: Task list items render as checkboxes
- **WHEN** a version containing `- [x] done` and `- [ ] todo` is rendered
- **THEN** each item shows a checkbox reflecting whether it is ticked
- **AND** neither item shows the literal text `[x]` or `[ ]`

#### Scenario: Checkboxes cannot be changed
- **WHEN** a reviewer interacts with a rendered task list checkbox
- **THEN** its state does not change
- **AND** no document content is modified

#### Scenario: Page reports document state
- **WHEN** a reviewer opens the review page
- **THEN** the page shows the document title, the version number, the review status,
  and the originating project path

#### Scenario: Page reports the originating session
- **GIVEN** a document submitted from a detected agent session
- **WHEN** a reviewer opens the review page
- **THEN** the page shows which tool the session belongs to
- **AND** the session identifier is available without leaving the page

#### Scenario: Page links to the other views
- **WHEN** a reviewer opens the review page for a version
- **THEN** a link to the raw line view of that version is present
- **AND** a link comparing it with its predecessor is present when one exists

#### Scenario: Unknown document is reported
- **WHEN** a reviewer opens a review page for a slug that does not exist
- **THEN** the response status is 404
