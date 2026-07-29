## MODIFIED Requirements

### Requirement: Documents record their provenance
A document SHALL record where it came from — project path, originating agent
tool, and agent session — so a reviewer facing several pending reviews can
tell which conversation in which project is waiting, and can find their way
back to it.

#### Scenario: Provenance is captured at submission
- **WHEN** a document is submitted with a title, an originating project path, and an
  agent session identifier
- **THEN** those values are stored on the document
- **AND** they are shown on the review page and in the pending list

#### Scenario: The session tool is stored beside the identifier
- **WHEN** a document is submitted from within an agent session
- **THEN** the document records which tool the session belongs to
- **AND** the tool is recorded even when the session identifier is
  unavailable

#### Scenario: Slug is derived when not supplied
- **WHEN** a document is submitted without an explicit slug
- **THEN** a slug is derived from the source file name
- **AND** the slug is unique within the store
