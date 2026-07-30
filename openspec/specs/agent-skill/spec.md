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
- **THEN** the skill instructs the agent to address each comment and resubmit the
  revised file under the same slug for a further round
- **AND** does not instruct any bookkeeping on the comments themselves, since
  resubmission supersedes them

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

### Requirement: The skill offers a hands-free way to learn the outcome
The skill SHALL instruct agents whose harness supports background tasks to
start `await` in the background after submitting, and to branch on the
completed task's exit code exactly as for `review` — while restating that no
review command may ever hold the agent's turn open in the foreground.

#### Scenario: Background awaiting is taught beside submit-and-stop
- **WHEN** an agent reads the skill's submission flow
- **THEN** it is instructed to start the await command as a background task
  when its harness offers one
- **AND** to end its turn as before rather than waiting in the foreground

#### Scenario: The completed wait is read like a review
- **WHEN** the background await completes
- **THEN** the skill instructs the agent to branch on its exit code with the
  same mapping as the review command

#### Scenario: Harnesses without background tasks lose nothing
- **WHEN** an agent's harness cannot run background tasks
- **THEN** the skill's flow is unchanged: submit, report the URL, stop, and
  read the outcome when nudged

### Requirement: The skill covers reviewing a set of files
The skill SHALL document how to submit several files as one review — the
multi-path `submit` invocation, that argument order is reading order, that
relative paths make the headings — and that review feedback names the source
file and line, so the agent edits the real files and resubmits the same set
under the same slug.

#### Scenario: The skill shows a file-set submission
- **WHEN** an agent needs a directory of related markdown reviewed as one
  decision
- **THEN** the skill provides the multi-path submit line, with a glob
  example and a note to submit from the directory that makes paths readable

#### Scenario: The skill explains where feedback lands
- **WHEN** a file-set review comes back with changes requested
- **THEN** the skill states that each comment names its source file and
  file-local line, and that the fix belongs in that file followed by a
  resubmission of the same set

