## ADDED Requirements

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
