## ADDED Requirements

### Requirement: A version is served as rendered markdown
The review page SHALL present a version as rendered HTML, not as raw markdown source,
because reading formatted prose is the reason the page exists.

#### Scenario: Markdown is rendered to HTML
- **WHEN** a reviewer opens the review page for a version
- **THEN** markdown constructs including headings, emphasis, lists, links, tables, and
  fenced code blocks are rendered as their HTML equivalents

#### Scenario: Page reports document state
- **WHEN** a reviewer opens the review page
- **THEN** the page shows the document title, the version number, the review status,
  and the originating project path

#### Scenario: Unknown document is reported
- **WHEN** a reviewer opens a review page for a slug that does not exist
- **THEN** the response status is 404

### Requirement: Every block carries its source line range
Each top-level rendered block SHALL be annotated with the line range of the markdown
source it was produced from, so that a comment can be anchored to an exact, immutable
region of the version.

#### Scenario: Blocks expose their source range
- **WHEN** a version is rendered
- **THEN** each addressable block element carries the start and end source line of the
  markdown that produced it

#### Scenario: Ranges are addressable at the granularity of a plan
- **WHEN** a version containing a heading, a multi-line paragraph, a bulleted list of
  three items, and a fenced code block is rendered
- **THEN** the heading, the paragraph, each individual list item, and the code block
  are each separately addressable
- **AND** their reported ranges lie within the bounds of the version's content

#### Scenario: Ranges resolve back to source text
- **WHEN** a block's reported line range is applied to the version content
- **THEN** the extracted text is the markdown source of that block

### Requirement: Rendered output is safe against injected markup
Document content and comment text are untrusted input. The page SHALL neither execute
nor honour markup embedded in them.

#### Scenario: Raw HTML in markdown is not executed
- **WHEN** a version whose markdown contains a `<script>` tag or an inline event
  handler attribute is rendered
- **THEN** that markup is emitted as visible text rather than active HTML
- **AND** no script is executed when the page loads

#### Scenario: Comment text is escaped
- **WHEN** a comment whose body contains HTML markup is displayed on the review page
- **THEN** the markup is shown as literal text
- **AND** it does not alter the structure of the page

#### Scenario: Link targets are constrained
- **WHEN** a version contains a link with a `javascript:` target
- **THEN** the rendered link does not carry that target
