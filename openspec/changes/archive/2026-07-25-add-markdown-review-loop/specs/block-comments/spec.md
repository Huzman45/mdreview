## ADDED Requirements

### Requirement: A comment is anchored to a line range within a version
The system SHALL let a reviewer attach a note to a specific region of a specific
version, identified by the source line range of the block being commented on.

#### Scenario: Comment is created against a block
- **WHEN** a reviewer submits a comment body for a block's line range on a version
- **THEN** the comment is stored against that version and range
- **AND** its state is `open`
- **AND** it is listed on the review page beside the block it refers to

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

### Requirement: Comments have stable human-readable references
Each comment SHALL carry a short reference that is stable within its version, so a
reviewer and an agent can refer to the same note unambiguously.

#### Scenario: References are assigned in creation order
- **WHEN** three comments are created on a version
- **THEN** they are referenced `C1`, `C2`, and `C3` in the order they were created

#### Scenario: References are scoped to a version
- **WHEN** a comment is created on version 2 of a document that already has comments
  on version 1
- **THEN** numbering for version 2 starts again at `C1`

#### Scenario: References survive resolution
- **WHEN** a comment referenced `C2` is resolved and the version's comments are listed
- **THEN** that comment is still referenced `C2`

### Requirement: Comments move through an explicit lifecycle
A comment SHALL be in exactly one of `open`, `resolved`, or `outdated`, so that both
reviewer and agent can tell what remains to be addressed.

#### Scenario: Resolving a comment closes it
- **GIVEN** an `open` comment
- **WHEN** it is resolved
- **THEN** its state becomes `resolved`
- **AND** it is excluded from the unresolved listing

#### Scenario: Resolving an already-resolved comment is idempotent
- **WHEN** a comment that is already `resolved` is resolved again
- **THEN** the request succeeds and the state remains `resolved`

#### Scenario: Unknown reference is reported
- **WHEN** resolution is requested for a reference that does not exist on the version
- **THEN** the request fails with an error naming the unknown reference

### Requirement: A new version supersedes prior comments
When a revision is submitted, comments on earlier versions SHALL be marked `outdated`
rather than relocated onto shifted line numbers.

#### Scenario: Open comments are superseded by a revision
- **GIVEN** a version with two `open` comments
- **WHEN** a new version of that document is recorded
- **THEN** both comments become `outdated`
- **AND** they remain readable against the version they were written on

#### Scenario: Resolved comments are left as resolved
- **GIVEN** a version with one `resolved` comment and one `open` comment
- **WHEN** a new version is recorded
- **THEN** the `resolved` comment stays `resolved`
- **AND** the `open` comment becomes `outdated`

#### Scenario: Anchors are never rewritten
- **WHEN** a new version is recorded
- **THEN** the line ranges and quoted text of all earlier comments are unchanged
