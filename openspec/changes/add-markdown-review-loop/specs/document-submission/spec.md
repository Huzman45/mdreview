## ADDED Requirements

### Requirement: Submitting markdown creates a reviewable version
The system SHALL accept markdown content under a document name and record it as a
new version awaiting review.

#### Scenario: First submission creates document and version
- **WHEN** markdown content is submitted under a document slug that does not yet exist
- **THEN** a document is created with that slug
- **AND** version 1 is recorded containing the exact submitted content
- **AND** that version's review status is `pending`
- **AND** the response includes the document slug, the version number, and the URL of
  the review page

#### Scenario: Submission returns immediately
- **WHEN** content is submitted
- **THEN** the response is returned without waiting for any human action

#### Scenario: Empty content is rejected
- **WHEN** content consisting only of whitespace is submitted
- **THEN** the submission is rejected with a validation error
- **AND** no document or version is created

### Requirement: Versions are immutable and content-addressed
A recorded version SHALL never be modified. Each version SHALL store the full content
and its SHA-256 digest, so that any anchor into it remains valid forever.

#### Scenario: Content and digest are stored together
- **WHEN** a version is recorded
- **THEN** the full content is stored verbatim
- **AND** the stored digest equals the SHA-256 of that content

#### Scenario: Existing versions are never rewritten
- **WHEN** a new version of a document is recorded
- **THEN** the content and digest of every earlier version are unchanged

### Requirement: Resubmission creates a successive version
Submitting a document again SHALL open a new review round as a new version, numbered
sequentially per document.

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

### Requirement: Unchanged resubmission does not create a redundant version
To keep the review history meaningful, resubmitting byte-identical content SHALL NOT
create a new version.

#### Scenario: Identical content is a no-op
- **GIVEN** a document whose latest version is `pending` with a known digest
- **WHEN** content with the same digest is submitted
- **THEN** no new version is created
- **AND** the response identifies the existing version and indicates it was reused

#### Scenario: Identical content after a decision opens a new round
- **GIVEN** a document whose latest version has already been decided
- **WHEN** byte-identical content is submitted
- **THEN** a new version is created so that a fresh decision can be recorded

### Requirement: Documents record their provenance
A document SHALL record where it came from, so a reviewer facing several pending
reviews can tell which agent in which project is waiting.

#### Scenario: Provenance is captured at submission
- **WHEN** a document is submitted with a title, an originating project path, and an
  agent session identifier
- **THEN** those values are stored on the document
- **AND** they are shown on the review page and in the pending list

#### Scenario: Slug is derived when not supplied
- **WHEN** a document is submitted without an explicit slug
- **THEN** a slug is derived from the source file name
- **AND** the slug is unique within the store
