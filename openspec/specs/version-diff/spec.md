# version-diff Specification

## Purpose
Comparing two versions of a document and presenting what changed between
them.

## Requirements
### Requirement: Two versions of a document can be compared
The system SHALL present the line differences between two versions of the same
document, so a reviewer can see what a revision actually changed instead of re-reading
it whole.

#### Scenario: Comparing consecutive versions
- **GIVEN** a document with versions 1 and 2
- **WHEN** a reviewer compares version 1 with version 2
- **THEN** lines present only in version 2 are marked as added
- **AND** lines present only in version 1 are marked as removed
- **AND** unchanged lines are shown as context

#### Scenario: Comparing non-adjacent versions
- **GIVEN** a document with versions 1, 2 and 3
- **WHEN** a reviewer compares version 1 with version 3
- **THEN** the differences between exactly those two versions are shown

#### Scenario: Identical content reports no differences
- **WHEN** two versions with identical content are compared
- **THEN** the view states that nothing changed

#### Scenario: Line numbers are shown for both sides
- **WHEN** a comparison is displayed
- **THEN** each line carries its line number in the version it belongs to

### Requirement: A comparison is reachable from a document
Finding a comparison SHALL not require constructing a URL by hand.

#### Scenario: A revision links to its comparison
- **GIVEN** a document with more than one version
- **WHEN** a reviewer views a version that has a predecessor
- **THEN** a link comparing it with its predecessor is offered

#### Scenario: A single-version document offers no comparison
- **GIVEN** a document with exactly one version
- **WHEN** the reviewer views it
- **THEN** no comparison link is offered

### Requirement: A comparison is read-only
A comparison describes the relationship between two versions and belongs to neither, so
it SHALL NOT accept comments or decisions.

#### Scenario: No comment form on a comparison
- **WHEN** a comparison is displayed
- **THEN** no comment form and no decision control is present

### Requirement: Invalid comparisons are rejected
A comparison naming a document or version that does not exist SHALL be reported as not
found rather than rendered as an empty diff.

#### Scenario: Unknown version is reported
- **WHEN** a comparison names a version that does not exist
- **THEN** the response status is 404

#### Scenario: Unknown document is reported
- **WHEN** a comparison names a document that does not exist
- **THEN** the response status is 404

