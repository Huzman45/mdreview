# diagram-rendering Specification

## Purpose
Turning a fenced diagram block into a rendered diagram in the browser,
including asset delivery, failure fallback, and the security posture for
rendering untrusted diagram source.

## Requirements
### Requirement: Diagram blocks render as diagrams
A fenced code block whose info string names a supported diagram language SHALL be
rendered as a diagram in the browser rather than as source text.

#### Scenario: A mermaid block is marked for rendering
- **WHEN** a version containing a fence tagged `mermaid` is rendered
- **THEN** the emitted markup identifies that block as a diagram to be rendered
- **AND** the original diagram source is preserved in the page

#### Scenario: Ordinary code fences are untouched
- **WHEN** a version contains a fence tagged with a programming language
- **THEN** it renders as a code block, not as a diagram

#### Scenario: Untagged fences are untouched
- **WHEN** a version contains a fence with no info string
- **THEN** it renders as a code block

### Requirement: A diagram remains an addressable block
Diagram rendering SHALL NOT remove a diagram from the set of commentable blocks, since
a diagram is often the thing a reviewer most wants to question.

#### Scenario: A diagram carries its source line range
- **WHEN** a version containing a diagram block is rendered
- **THEN** that block carries the source line range of the fence
- **AND** the range resolves back to the fence in the version content

### Requirement: A failed diagram never hides content
Diagram source comes from an agent and may be malformed. A diagram that cannot be
rendered SHALL fall back to showing its source.

#### Scenario: Malformed diagram falls back to source
- **WHEN** a diagram block contains source the renderer cannot parse
- **THEN** the block displays the diagram source as text
- **AND** an indication that the diagram could not be rendered is shown

#### Scenario: Missing renderer falls back to source
- **WHEN** the diagram library is unavailable
- **THEN** diagram blocks display their source as text rather than appearing empty

### Requirement: Diagram source is treated as untrusted
The diagram renderer SHALL be configured so that markup embedded in diagram labels
cannot execute, consistent with how the rest of the page treats document content.

#### Scenario: Markup in a diagram label does not execute
- **WHEN** a diagram contains a node label with an embedded script tag
- **THEN** no script from that label executes when the diagram renders

### Requirement: Diagram assets are only fetched when needed
The diagram library is large. It SHALL be delivered from the application itself rather
than a third party, and SHALL only be requested by pages that contain a diagram.

#### Scenario: A page without diagrams does not request the library
- **WHEN** a version containing no diagram blocks is rendered
- **THEN** the page does not load the diagram library

#### Scenario: A page with a diagram requests the library locally
- **WHEN** a version containing a diagram block is rendered
- **THEN** the page loads the diagram library from this application's own static assets

### Requirement: Diagrams follow the active colour scheme
A diagram SHALL be rendered with a theme matching the page's active colour scheme. A
diagram rendered with light colours on a dark page is unreadable.

#### Scenario: Diagram theme matches the page
- **WHEN** a diagram is rendered while the dark colour scheme is active
- **THEN** the diagram uses a dark-appropriate theme

