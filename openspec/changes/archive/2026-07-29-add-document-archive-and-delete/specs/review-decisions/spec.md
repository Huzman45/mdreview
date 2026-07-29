## MODIFIED Requirements

### Requirement: Pending reviews are discoverable
The system SHALL expose which active documents are awaiting a decision, so that
a reviewer with several agents in flight can find them without hunting for
URLs. Archived documents are not awaiting anything and stay out of these
listings.

#### Scenario: Index lists documents awaiting review
- **GIVEN** three documents, two of which have a `pending` latest version
- **WHEN** the reviewer opens the index
- **THEN** the two pending documents are listed with their title, project path, and
  version number
- **AND** each links to its review page

#### Scenario: Decided documents are distinguishable
- **WHEN** the reviewer opens the index
- **THEN** documents whose latest version has been decided show that decision rather
  than appearing as awaiting review

#### Scenario: Pending list can be filtered
- **WHEN** the list of documents is requested restricted to pending reviews
- **THEN** only active documents whose latest version is `pending` are returned

#### Scenario: Archived documents are absent from the index
- **GIVEN** an archived document
- **WHEN** the reviewer opens the index
- **THEN** it is not listed among waiting or decided documents
