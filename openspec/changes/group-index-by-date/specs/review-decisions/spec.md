## MODIFIED Requirements

### Requirement: Pending reviews are discoverable
The system SHALL expose which active documents are awaiting a decision, so that
a reviewer with several agents in flight can find them without hunting for
URLs. Archived documents are not awaiting anything and stay out of these
listings. Decided documents are history and are presented grouped by day, so
the recent past can be scanned without reading timestamps.

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

#### Scenario: Decided documents are grouped by day
- **GIVEN** decided documents whose latest versions arrived on different days
- **WHEN** the reviewer opens the index
- **THEN** the decided documents appear under one heading per calendar day,
  most recent day first
- **AND** the current day is labelled Today and the previous one Yesterday

#### Scenario: The waiting queue is not sliced by day
- **GIVEN** documents awaiting review submitted on different days
- **WHEN** the reviewer opens the index
- **THEN** they are listed as one queue, newest first, with no day headings

#### Scenario: Pending list can be filtered
- **WHEN** the list of documents is requested restricted to pending reviews
- **THEN** only active documents whose latest version is `pending` are returned

#### Scenario: Archived documents are absent from the index
- **GIVEN** an archived document
- **WHEN** the reviewer opens the index
- **THEN** it is not listed among waiting or decided documents
