## ADDED Requirements

### Requirement: A version can be viewed as numbered source lines
The system SHALL offer a view of a version as its raw markdown, one numbered line at a
time, so that feedback can target text no rendered block isolates.

#### Scenario: Raw view lists every line with its number
- **WHEN** a reviewer opens the raw view of a version
- **THEN** every line of the version content is shown in order with its 1-based line
  number
- **AND** the markdown is shown as literal source rather than rendered

#### Scenario: Raw view reports document state
- **WHEN** a reviewer opens the raw view
- **THEN** the document title, version number, and review status are shown

#### Scenario: The two views are reachable from each other
- **WHEN** a reviewer is on either the rendered or the raw view
- **THEN** a link to the other view for the same version is present

#### Scenario: Unknown document or version is reported
- **WHEN** the raw view is requested for a slug or version that does not exist
- **THEN** the response status is 404

### Requirement: Any line range can be commented on
The raw view SHALL allow a comment to be anchored to a single line or a contiguous
range of lines, including ranges that fall inside a fenced code block or partway
through a wrapped paragraph.

#### Scenario: Commenting on one line inside a fence
- **GIVEN** a version whose lines 10 to 14 are a fenced code block
- **WHEN** a reviewer comments on line 12 from the raw view
- **THEN** the comment is stored with that single line as its anchor
- **AND** its quoted source is exactly that line

#### Scenario: Commenting on a contiguous range
- **WHEN** a reviewer selects lines 4 to 6 and comments
- **THEN** the comment is anchored to lines 4 to 6
- **AND** its quoted source is those three lines

#### Scenario: Raw comments appear alongside block comments
- **WHEN** a comment created from the raw view is listed for its version
- **THEN** it appears in the same list as comments created from the rendered view
- **AND** it is indistinguishable in structure from them

#### Scenario: Anchors are still bounds-checked
- **WHEN** a comment is requested for a line beyond the end of the version
- **THEN** it is rejected, exactly as for the rendered view

### Requirement: The raw view respects the review lifecycle
Commenting from the raw view SHALL be offered under the same conditions as the
rendered view, so the two cannot disagree about whether a round is open.

#### Scenario: A decided version is read-only in the raw view
- **GIVEN** a version whose review has been decided
- **WHEN** its raw view is opened
- **THEN** no comment form is offered

#### Scenario: A superseded version is read-only in the raw view
- **GIVEN** a version that is not the latest
- **WHEN** its raw view is opened
- **THEN** no comment form is offered
