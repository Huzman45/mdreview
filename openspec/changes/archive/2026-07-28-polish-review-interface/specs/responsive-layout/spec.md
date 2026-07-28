## ADDED Requirements

### Requirement: No page is wider than the screen
No page SHALL require horizontal scrolling of the document at any supported width.
Content too wide to fit, such as a table or a code block, MUST scroll within its own
container rather than widening the page.

#### Scenario: Every page fits a phone
- **WHEN** the index, a rendered document, a source view, and a comparison are each
  opened at a phone width
- **THEN** the document's scrollable width equals its visible width for each

#### Scenario: Every page fits a tablet in both orientations
- **WHEN** each page type is opened at tablet portrait and tablet landscape widths
- **THEN** none requires horizontal scrolling

#### Scenario: A long identifier does not widen the page
- **GIVEN** a document containing an inline code span too long to fit on one line
- **WHEN** it is rendered at a phone width
- **THEN** the span wraps within the viewport
- **AND** the page does not scroll horizontally

#### Scenario: A wide table scrolls within itself
- **GIVEN** a document containing a table wider than the viewport
- **WHEN** it is rendered at a phone width
- **THEN** the table scrolls horizontally within its own bounds
- **AND** the page itself does not

### Requirement: The layout is verified in a real browser
Because this class of defect is invisible to assertions about markup, conformance
SHALL be checked by measuring layout in a browser.

#### Scenario: The check reports the offending element
- **WHEN** a page exceeds the viewport width
- **THEN** the failure identifies the widest offending element, not merely that
  overflow occurred

#### Scenario: The check is skipped rather than failing when unavailable
- **WHEN** the test suite runs on a machine with no browser installed
- **THEN** these checks are skipped and the rest of the suite still runs

### Requirement: The interface can be reviewed by eye
A reproducible way to see every page SHALL be kept in the repository, so a visual
change can be assessed without rebuilding the viewport list by hand.

#### Scenario: Every combination is captured
- **WHEN** the screenshot harness runs
- **THEN** it captures each page type at each supported width in both colour schemes

#### Scenario: The harness reports layout problems it finds
- **WHEN** the harness captures a page that overflows or has the wrong scheme applied
- **THEN** it reports that page as a problem and exits non-zero
