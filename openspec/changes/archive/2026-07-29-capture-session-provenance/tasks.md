## 1. Capture

- [x] 1.1 `session.py`: detection with the D2 precedence and id-format tool
  inference
- [x] 1.2 CLI submit sends `session_tool` and `session_id` from detection
- [x] 1.3 `contrib/opencode/mdreview-session.js` shell.env plugin;
  `mise run setup` installs it

## 2. Storage and API

- [x] 2.1 Migration step 4: `documents.session_tool`, backfilled from id
  shapes
- [x] 2.2 `Document.session_tool` through store and submit
- [x] 2.3 API: submit accepts, document response returns, both fields

## 3. Surface

- [x] 3.1 Colophon: tool and shortened id, full id on hover
- [x] 3.2 Index row sub-line names the tool
- [x] 3.3 README documents the plugin and the detection order

## 4. Verification

- [x] 4.1 Detection units: precedence, inference, scrubbed-id fallbacks,
  nothing detected
- [x] 4.2 Migration test: backfill of both id shapes
- [x] 4.3 End-to-end: a submit with agent env pinned lands tool and id in the
  API and on the page
- [x] 4.4 Full suite, ruff, screenshot harness
