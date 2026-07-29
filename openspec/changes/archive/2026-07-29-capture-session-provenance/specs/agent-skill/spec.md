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
- **AND** the opencode session plugin is installed, so submissions from
  opencode carry their session identity

#### Scenario: Re-running the setup refreshes a stale skill
- **WHEN** the skill file in the repository has changed and the setup command is run
  again
- **THEN** the installed skill matches the repository version
