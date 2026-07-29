## ADDED Requirements

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
