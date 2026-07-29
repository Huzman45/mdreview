## ADDED Requirements

### Requirement: A comment can be anchored to a run of consecutive blocks
The rendered view SHALL let the reviewer extend a block selection to a
contiguous run of blocks with shift-click, using the same gesture as the source
view, and anchor one comment to the whole span. The anchor is the line range
from the first covered line to the last; it is stored no differently from a
range drawn in the source view.

#### Scenario: Shift-click extends the selection downward
- **GIVEN** a selected block
- **WHEN** the reviewer shift-clicks a later block
- **THEN** the pending comment's anchor spans from the first block's start line
  to the later block's end line

#### Scenario: Shift-click extends the selection upward
- **GIVEN** a selected block
- **WHEN** the reviewer shift-clicks an earlier block
- **THEN** the anchor spans from the earlier block's start line to the selected
  block's end line

#### Scenario: Blocks between the endpoints are included
- **WHEN** a selection is extended across intervening blocks
- **THEN** every block inside the span is visibly selected
- **AND** the anchor covers their lines whether or not they were clicked

#### Scenario: A plain click starts over
- **GIVEN** an extended selection
- **WHEN** the reviewer clicks a block without shift
- **THEN** the selection is that single block again

#### Scenario: The comment stores the extended range
- **WHEN** a comment is submitted from an extended selection
- **THEN** it is anchored to the span's line range
- **AND** its quoted source is the markdown of that whole span
