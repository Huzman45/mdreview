# block-comments Specification

## Purpose
Creating, editing, deleting and listing comments anchored to a block's line
range within one version, and the open / outdated lifecycle they move through
as versions accumulate.
## Requirements
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

### Requirement: An open comment can be edited
The reviewer SHALL be able to change the body of an `open` comment. The anchor and
the quoted source captured at creation are immutable: an edit changes what the note
says, never what it points at.

#### Scenario: Body is edited in place
- **GIVEN** an `open` comment
- **WHEN** the reviewer saves a new body for it
- **THEN** the stored body is replaced
- **AND** its reference, line range, quoted source, and state are unchanged

#### Scenario: An edited comment is marked as edited
- **WHEN** an `open` comment's body has been edited
- **THEN** the review page shows it as edited

#### Scenario: An edit cannot empty a comment
- **WHEN** a comment edit is submitted with a body consisting only of whitespace
- **THEN** the request is rejected with a validation error
- **AND** the stored body is unchanged

#### Scenario: An outdated comment cannot be edited
- **GIVEN** a comment that is `outdated`
- **WHEN** an edit is submitted for it
- **THEN** the request is rejected
- **AND** the comment is unchanged

### Requirement: An open comment can be deleted
The reviewer SHALL be able to delete an `open` comment, removing it from the review
entirely. Deletion is offered behind a confirmation, since it destroys the
reviewer's own writing.

#### Scenario: Deleting removes the comment
- **GIVEN** an `open` comment
- **WHEN** the reviewer confirms its deletion
- **THEN** it no longer appears in any comment listing
- **AND** it no longer counts toward the version's open comments

#### Scenario: An outdated comment cannot be deleted
- **GIVEN** a comment that is `outdated`
- **WHEN** deletion is requested for it
- **THEN** the request is rejected
- **AND** the comment remains readable

#### Scenario: Unknown reference is reported
- **WHEN** deletion is requested for a reference that does not exist on the version
- **THEN** the request fails with an error naming the unknown reference

### Requirement: Comment references are never reused
Each comment SHALL carry a short reference that is stable within its version, so a
reviewer and an agent can refer to the same note unambiguously. A reference, once
assigned, is never given to different feedback — not even after the comment holding
it is deleted.

#### Scenario: References are assigned in creation order
- **WHEN** three comments are created on a version
- **THEN** they are referenced `C1`, `C2`, and `C3` in the order they were created

#### Scenario: References are scoped to a version
- **WHEN** a comment is created on version 2 of a document that already has comments
  on version 1
- **THEN** numbering for version 2 starts again at `C1`

#### Scenario: A deleted reference is not reused
- **GIVEN** a version with comments `C1` and `C2`
- **WHEN** `C2` is deleted and a new comment is created on that version
- **THEN** the new comment is referenced `C3`
- **AND** no comment on that version is ever again referenced `C2`

#### Scenario: References survive editing
- **WHEN** a comment referenced `C2` is edited and the version's comments are listed
- **THEN** that comment is still referenced `C2`

### Requirement: A comment is open until a revision supersedes it
A comment SHALL be in exactly one of `open` or `outdated`, so that both reviewer and
agent can tell what remains to be addressed. `open` means the note awaits the agent;
`outdated` means a later version superseded it. Nothing else closes a comment: the
reviewer who no longer stands by a note edits or deletes it instead.

#### Scenario: A comment opens as open
- **WHEN** a comment is created
- **THEN** its state is `open`
- **AND** it counts toward the version's open comments

#### Scenario: Only a revision closes a comment
- **GIVEN** an `open` comment
- **WHEN** a new version of the document is recorded
- **THEN** the comment's state becomes `outdated`
- **AND** no operation other than a revision changes a comment's state

### Requirement: A revision outdates prior comments
When a revision is submitted, comments on earlier versions SHALL be marked `outdated`
rather than relocated onto shifted line numbers.

#### Scenario: Open comments are superseded by a revision
- **GIVEN** a version with two `open` comments
- **WHEN** a new version of that document is recorded
- **THEN** both comments become `outdated`
- **AND** they remain readable against the version they were written on

#### Scenario: Edited comments are superseded like any other
- **GIVEN** a version with an `open` comment that has been edited
- **WHEN** a new version is recorded
- **THEN** that comment becomes `outdated`
- **AND** its edited body is what remains on record

#### Scenario: Anchors are never rewritten
- **WHEN** a new version is recorded
- **THEN** the line ranges and quoted text of all earlier comments are unchanged

