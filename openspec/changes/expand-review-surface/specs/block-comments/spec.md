## MODIFIED Requirements

### Requirement: A comment is anchored to a line range within a version
The system SHALL let a reviewer attach a note to a specific region of a specific
version, identified by a line range within that version. The range MAY correspond to a
rendered block, but is not required to: any contiguous range of lines inside the version
is a valid anchor, which is what allows feedback on a single line of a fenced block.

#### Scenario: Comment is created against a block
- **WHEN** a reviewer submits a comment body for a block's line range on a version
- **THEN** the comment is stored against that version and range
- **AND** its state is `open`
- **AND** it is listed on the review page beside the block it refers to

#### Scenario: Comment is created against an arbitrary line range
- **WHEN** a reviewer submits a comment for a line range that no rendered block
  covers on its own
- **THEN** the comment is stored against that version and range
- **AND** it is listed alongside comments anchored to whole blocks

#### Scenario: Quoted source is captured at creation
- **WHEN** a comment is created for a line range
- **THEN** the markdown source text of that range is stored with the comment
- **AND** that quoted text is available without re-reading the document

#### Scenario: Out-of-bounds anchor is rejected
- **WHEN** a comment is submitted for a line range that falls outside the version's
  content
- **THEN** the request is rejected with a validation error
- **AND** no comment is stored

#### Scenario: Empty comment body is rejected
- **WHEN** a comment is submitted with a body consisting only of whitespace
- **THEN** the request is rejected with a validation error
