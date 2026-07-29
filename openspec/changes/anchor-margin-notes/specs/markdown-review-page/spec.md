## ADDED Requirements

### Requirement: Margin notes sit beside what they annotate
In the two-column layout the margin SHALL place each note at the vertical
position of its anchor — the line it targets, located proportionally within a
multi-line block — so the association between remark and passage is carried
by position rather than by reading references.

#### Scenario: A note aligns with its block
- **GIVEN** a comment anchored to a paragraph
- **WHEN** the review page is shown in the two-column layout
- **THEN** the note's top edge aligns with the paragraph's vertical position

#### Scenario: A note into a long block points into it
- **GIVEN** a comment anchored to a line in the middle of a fenced code block
- **WHEN** the page is shown in the two-column layout
- **THEN** the note sits beside the interior of the fence, below its top edge

#### Scenario: Notes sharing an anchor stack downward
- **GIVEN** two comments anchored to the same block
- **WHEN** the page is shown in the two-column layout
- **THEN** the first note holds the anchor position
- **AND** the second sits fully below the first without overlapping it

#### Scenario: Every note remains fully visible
- **WHEN** notes are displaced downward by earlier notes
- **THEN** no note is clipped, hidden, or overlapped
- **AND** the page grows as needed to hold the last note

#### Scenario: The comment form follows the selection
- **GIVEN** a block is selected for commenting
- **WHEN** the page is shown in the two-column layout
- **THEN** the comment form is positioned beside the selected region

#### Scenario: The narrow layout keeps the stacked list
- **WHEN** the page is narrower than the two-column breakpoint
- **THEN** notes appear as the existing stacked list below the prose
- **AND** no note is absolutely positioned

#### Scenario: Hovering a note indicates its target
- **WHEN** the reviewer hovers a note in the two-column layout
- **THEN** the annotated region in the prose is visibly indicated
