# agent-skill Specification

## Purpose
The packaged instructions that make an agent reach for this tool when it
produces a plan, and read the decision back correctly when resumed.

## Requirements
### Requirement: A skill teaches agents the review protocol
The project SHALL ship an agent skill describing when and how to use the tool, so the
loop works without the operator remembering any commands.

#### Scenario: Skill is discoverable by the agent
- **WHEN** the skill is installed into the user's skills directory
- **THEN** it exposes a name and a description stating that it applies when an agent
  has produced a plan or design document for human review

#### Scenario: Skill documents the submit-and-stop step
- **WHEN** an agent follows the skill after writing a plan file
- **THEN** it is instructed to submit the file, report the returned URL to the user,
  and then stop rather than continuing to implement

#### Scenario: Skill documents reading the outcome on resume
- **WHEN** an agent following the skill is nudged after a review
- **THEN** it is instructed to run the review command as its first action
- **AND** to branch on the exit code

### Requirement: The skill maps every exit code to an action
Ambiguity about the outcome is the main failure mode of a hands-off loop, so the skill
SHALL state what to do for each documented exit status.

#### Scenario: Approved outcome proceeds
- **WHEN** the review command exits 0
- **THEN** the skill instructs the agent to proceed with implementation

#### Scenario: Changes requested drives a revision
- **WHEN** the review command exits 2
- **THEN** the skill instructs the agent to address each comment, resolve the ones it
  has addressed, and resubmit the revised file for a further round

#### Scenario: Pending outcome does not proceed
- **WHEN** the review command exits 3
- **THEN** the skill instructs the agent to tell the user the review is still
  outstanding and to wait
- **AND** explicitly forbids proceeding as though approval had been given

#### Scenario: Cancelled outcome stops the work
- **WHEN** the review command exits 4
- **THEN** the skill instructs the agent to stop and ask the user how to proceed

### Requirement: Project instructions point at the tool
The repository SHALL document the loop so that an operator can wire it into their own
agent configuration.

#### Scenario: Instruction snippet is provided
- **WHEN** an operator reads the project documentation
- **THEN** it contains a snippet suitable for pasting into an agent instructions file
- **AND** the snippet states that plan files should be submitted for review rather than
  presented as chat text

#### Scenario: Installation is documented
- **WHEN** an operator reads the project documentation
- **THEN** it states where the skill must be installed for their agent to find it

