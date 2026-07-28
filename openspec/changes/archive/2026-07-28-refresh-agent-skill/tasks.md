## 1. Refresh the skill and make installation reproducible

- [x] 1.1 Describe the renderer's capabilities in the skill: task lists as read-only
  checkboxes, `mermaid` fences as diagrams with source fallback, and per-block comment
  granularity with advice to write small blocks
- [x] 1.2 Describe the rendered, source and changes views, and state that a comment may
  target a single line inside a fenced block
- [x] 1.3 Describe reviewing from another device: explicit LAN startup, the tokenised
  URL, loopback being unaffected, and the address changing with DHCP
- [x] 1.4 Add `install-cli`, `install-skill` and a `setup` task that installs both,
  writing the skill to one canonical location and symlinking it for Claude Code
- [x] 1.5 Rewrite the README install section around the setup task, stating the
  editable install's failure mode and the non-editable alternative
- [x] 1.6 Verify the task installs from a clean state and refreshes a stale skill
- [x] 1.7 Confirm the installed skill is discoverable by both runtimes and that the
  CLI runs from a directory outside the checkout
