## MODIFIED Requirements

### Requirement: Resubmission creates a successive version
Submitting a document again SHALL open a new review round as a new version, numbered
sequentially per document. If the document was archived, submitting a new version
reactivates it: a round the reviewer cannot see is a round that does not exist.

#### Scenario: Revised content becomes the next version
- **GIVEN** a document whose latest version is 1
- **WHEN** different content is submitted under the same slug
- **THEN** version 2 is recorded with review status `pending`
- **AND** version 1 remains readable at its own version number

#### Scenario: Version numbers are per document
- **GIVEN** two documents each with one version
- **WHEN** a second version is submitted for one of them
- **THEN** that document has versions 1 and 2
- **AND** the other document still has only version 1

#### Scenario: Resubmission reactivates an archived document
- **GIVEN** an archived document
- **WHEN** a new version is submitted under its slug
- **THEN** the document is no longer archived
- **AND** the new version appears on the index awaiting review
