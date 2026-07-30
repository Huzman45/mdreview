# markdown-review-page Specification

## Purpose
Rendering a version as HTML in which every block carries the source line
range it came from, so prose can be read and addressed at the same time.
## Requirements
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

### Requirement: A comment can be anchored to a run of consecutive blocks
The rendered view SHALL let the reviewer extend a block selection to a
contiguous run of blocks with shift-click, using the same gesture as the source
view, and anchor one comment to the whole span. The anchor is the line range
from the first covered line to the last; it is stored no differently from a
range drawn in the source view.

#### Scenario: Shift-click extends the selection downward
- **GIVEN** a selected block
- **WHEN** the reviewer shift-clicks a later block
- **THEN** the pending comment's anchor spans from the first block's start line
  to the later block's end line

#### Scenario: Shift-click extends the selection upward
- **GIVEN** a selected block
- **WHEN** the reviewer shift-clicks an earlier block
- **THEN** the anchor spans from the earlier block's start line to the selected
  block's end line

#### Scenario: Blocks between the endpoints are included
- **WHEN** a selection is extended across intervening blocks
- **THEN** every block inside the span is visibly selected
- **AND** the anchor covers their lines whether or not they were clicked

#### Scenario: A plain click starts over
- **GIVEN** an extended selection
- **WHEN** the reviewer clicks a block without shift
- **THEN** the selection is that single block again

#### Scenario: The comment stores the extended range
- **WHEN** a comment is submitted from an extended selection
- **THEN** it is anchored to the span's line range
- **AND** its quoted source is the markdown of that whole span

### Requirement: Margin notes sit beside what they annotate
In the two-column layout the margin SHALL place each note at the vertical
position of its anchor — the line it targets, located proportionally within a
multi-line block — so the association between remark and passage is carried
by position rather than by reading references.

#### Scenario: A note aligns with its block
- **GIVEN** a comment anchored to a paragraph
- **WHEN** the review page is shown in the two-column layout
- **THEN** the note's top edge aligns with the paragraph's vertical position

#### Scenario: A note into a long block points into it
- **GIVEN** a comment anchored to a line in the middle of a fenced code block
- **WHEN** the page is shown in the two-column layout
- **THEN** the note sits beside the interior of the fence, below its top edge

#### Scenario: Notes sharing an anchor stack downward
- **GIVEN** two comments anchored to the same block
- **WHEN** the page is shown in the two-column layout
- **THEN** the first note holds the anchor position
- **AND** the second sits fully below the first without overlapping it

#### Scenario: Every note remains fully visible
- **WHEN** notes are displaced downward by earlier notes
- **THEN** no note is clipped, hidden, or overlapped
- **AND** the page grows as needed to hold the last note

#### Scenario: The comment form follows the selection
- **GIVEN** a block is selected for commenting
- **WHEN** the page is shown in the two-column layout
- **THEN** the comment form is positioned beside the selected region

#### Scenario: The narrow layout keeps the stacked list
- **WHEN** the page is narrower than the two-column breakpoint
- **THEN** notes appear as the existing stacked list below the prose
- **AND** no note is absolutely positioned

#### Scenario: Hovering a note indicates its target
- **WHEN** the reviewer hovers a note in the two-column layout
- **THEN** the annotated region in the prose is visibly indicated

### Requirement: Top-level parts are visibly separated
The review page SHALL treat every top-level heading after the first as the
opening of a new part and separate it visibly from the part above, so a
document assembled from several files reads as its files rather than as one
undifferentiated scroll. The treatment applies to any document with several
top-level headings; the page has no notion of files.

#### Scenario: A second top-level heading opens a visibly new part
- **WHEN** a rendered document contains more than one `<h1>`
- **THEN** each `<h1>` after the first is separated from the preceding
  content by more than ordinary heading spacing

#### Scenario: A single-heading document is unaffected
- **WHEN** a rendered document contains one `<h1>`
- **THEN** its spacing is unchanged

