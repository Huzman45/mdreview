# document-lifecycle Specification

## Purpose
Putting whole documents away — reversibly from the browser, permanently from
the command line — without ever leaving an agent waiting on a review that
will not happen.
## Requirements
### Requirement: A document can be archived from the index
The reviewer SHALL be able to archive a document from the index. An archived
document leaves the index and the pending listings, but every page of its
history remains readable at its existing URLs.

#### Scenario: Archiving removes a document from the index
- **GIVEN** a document on the index
- **WHEN** the reviewer archives it
- **THEN** it no longer appears on the index
- **AND** its review pages remain readable

#### Scenario: Archived documents are excluded from pending listings
- **GIVEN** an archived document whose latest version is not decided
- **WHEN** pending documents are listed
- **THEN** the archived document is not among them

#### Scenario: The time of archiving is recorded
- **WHEN** a document is archived
- **THEN** the time it was archived is stored and shown in the archived
  listing

### Requirement: Archiving an undecided document cancels its round
Archiving a document whose latest version is `pending` SHALL cancel that
round, so an agent reading the outcome is told to stop rather than left
polling a review nobody will do.

#### Scenario: A pending round is cancelled by archiving
- **GIVEN** a document whose latest version is `pending`
- **WHEN** it is archived
- **THEN** that version's status becomes `cancelled`
- **AND** its decision note records that the document was archived without
  review

#### Scenario: A decided round is untouched by archiving
- **GIVEN** a document whose latest version is `approved`
- **WHEN** it is archived
- **THEN** the version's status and decision note are unchanged

### Requirement: An archived document can be restored
The reviewer SHALL be able to restore an archived document, returning it to
the index exactly as it was left.

#### Scenario: Restoring returns a document to the index
- **GIVEN** an archived document
- **WHEN** the reviewer restores it from the archived listing
- **THEN** it appears on the index again
- **AND** its review state is whatever it was when archived

#### Scenario: Archived documents are listed with a way back
- **WHEN** the reviewer opens the archived listing
- **THEN** each archived document is shown with when it was archived
- **AND** each offers a restore action

### Requirement: A new version reactivates an archived document
Submitting a new version of an archived document SHALL clear its archived
state, so the round it opens is visible where the reviewer looks.

#### Scenario: Resubmission brings a document back
- **GIVEN** an archived document
- **WHEN** a new version of it is submitted
- **THEN** the document reappears on the index awaiting review

### Requirement: A document can be deleted from the command line
The CLI SHALL offer permanent deletion of a document and its entire history,
guarded by an interactive confirmation. Deletion is not offered in the
browser.

#### Scenario: Deletion requires confirmation
- **WHEN** `delete` is run for an existing document without pre-approval
- **THEN** the command states that the document, its versions, and their
  comments will be permanently removed
- **AND** nothing is deleted unless the reviewer confirms

#### Scenario: Confirmed deletion removes everything
- **WHEN** deletion is confirmed
- **THEN** the document, all its versions, and all their comments are removed
- **AND** its slug no longer resolves

#### Scenario: Deletion can be pre-approved for scripts
- **WHEN** `delete` is run with the yes flag
- **THEN** no prompt is shown and the document is removed

#### Scenario: Declining leaves everything in place
- **WHEN** the reviewer declines the confirmation
- **THEN** the document and its history are unchanged
- **AND** the command exits without error

#### Scenario: Deleting an unknown slug fails clearly
- **WHEN** `delete` is run for a slug that does not exist
- **THEN** the command fails with a message naming the slug

