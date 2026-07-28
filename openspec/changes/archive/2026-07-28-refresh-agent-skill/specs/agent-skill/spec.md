## ADDED Requirements

### Requirement: The skill states what the renderer can display
The skill SHALL tell agents which markdown constructs the review page renders
semantically, so a plan is written to be reviewed rather than degraded to plain text.

#### Scenario: Task lists are described as usable
- **WHEN** an agent reads the skill
- **THEN** it learns that `- [x]` and `- [ ]` render as checkboxes
- **AND** that they are read-only for the reviewer, who will comment instead of
  ticking them

#### Scenario: Diagrams are described as usable
- **WHEN** an agent reads the skill
- **THEN** it learns that a fence tagged as a supported diagram language renders as a
  diagram
- **AND** that a diagram which fails to parse shows its source rather than vanishing

#### Scenario: Block granularity is described
- **WHEN** an agent reads the skill
- **THEN** it learns that each heading, paragraph, list item, table, diagram and code
  block is separately commentable
- **AND** is advised to structure documents in small blocks so feedback can be precise

### Requirement: The skill describes the available views
The skill SHALL describe each view of a version, so an agent can direct a reviewer
looking for a capability rather than guessing.

#### Scenario: All three views are named
- **WHEN** an agent reads the skill
- **THEN** it learns of the rendered view, the source view, and the changes view
- **AND** learns that the source view is how a reviewer comments on one line inside a
  fenced block

#### Scenario: Line-precise feedback is anticipated
- **WHEN** an agent reads the skill
- **THEN** it is told a comment may target a single line
- **AND** to read the reported line range rather than assuming a whole block

### Requirement: The skill covers reviewing from another device
The skill SHALL explain how to expose a review to another device on the same private
network, since the reviewer cannot discover this from the default output.

#### Scenario: LAN startup is described
- **WHEN** an agent reads the skill
- **THEN** it learns the server must be started explicitly on a private address
- **AND** that the printed URL carries a token the reviewer opens once
- **AND** that loopback requests are unaffected, so its own commands need nothing

#### Scenario: A changing address is anticipated
- **WHEN** an agent reads the skill
- **THEN** it learns the private address changes with DHCP, and that a link which
  stops loading probably means the address moved

## MODIFIED Requirements

### Requirement: Project instructions point at the tool
The repository SHALL document the loop so that an operator can wire it into their own
agent configuration, and SHALL provide a single reproducible command that installs the
CLI and the skill.

#### Scenario: Instruction snippet is provided
- **WHEN** an operator reads the project documentation
- **THEN** it contains a snippet suitable for pasting into an agent instructions file
- **AND** the snippet states that plan files should be submitted for review rather than
  presented as chat text

#### Scenario: Installation is documented
- **WHEN** an operator reads the project documentation
- **THEN** it states where the skill must be installed for their agent to find it

#### Scenario: Installation is a single command
- **WHEN** an operator runs the documented setup command
- **THEN** the CLI is placed on their `PATH`
- **AND** the skill is installed where both opencode and Claude Code will find it,
  from one source of truth rather than two copies that can diverge

#### Scenario: Re-running the setup refreshes a stale skill
- **WHEN** the skill file in the repository has changed and the setup command is run
  again
- **THEN** the installed skill matches the repository version
