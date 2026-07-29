## 1. Command

- [x] 1.1 `mdreview await <slug>` polling the state endpoint every two
  seconds until the latest version is decided
- [x] 1.2 `--timeout` (default eight hours) exiting 3; sixty consecutive
  unreachable seconds exiting 5; a wait that never reached the server
  reports 5, not 3
- [x] 1.3 Final output is `review`'s report, exit code is `review`'s code

## 2. Guidance

- [x] 2.1 Skill: background-await instruction beside submit-and-stop; the
  never-block-your-turn rule restated
- [x] 2.2 README: the command and the loop it closes

## 3. Verification

- [x] 3.1 Already-decided document returns immediately with the outcome
- [x] 3.2 A decision recorded mid-wait ends the wait with its code and report
- [x] 3.3 Timeout exits 3; unreachable-throughout exits 5
- [x] 3.4 Full suite, ruff
