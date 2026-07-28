## MODIFIED Requirements

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
