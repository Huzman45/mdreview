## ADDED Requirements

### Requirement: Top-level parts are visibly separated
The review page SHALL treat every top-level heading after the first as the
opening of a new part and separate it visibly from the part above, so a
document assembled from several files reads as its files rather than as one
undifferentiated scroll. The treatment applies to any document with several
top-level headings; the page has no notion of files.

#### Scenario: A second top-level heading opens a visibly new part
- **WHEN** a rendered document contains more than one `<h1>`
- **THEN** each `<h1>` after the first is separated from the preceding
  content by more than ordinary heading spacing

#### Scenario: A single-heading document is unaffected
- **WHEN** a rendered document contains one `<h1>`
- **THEN** its spacing is unchanged
