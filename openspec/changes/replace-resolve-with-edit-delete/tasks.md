## 1. Storage

- [x] 1.1 Migration step 2: rebuild `comments` with `CHECK (state IN ('open','outdated'))`
  and an `edited_at` column; map `resolved → outdated` in the copy; recreate the index
- [x] 1.2 Drop `CommentState.RESOLVED`; add `edited_at` to the `Comment` model
- [x] 1.3 Replace `resolve_comment` with `update_comment` (body only, stamps `edited_at`,
  refuses non-open) and `delete_comment` (refuses non-open)
- [x] 1.4 Allocate references from a `comment_seq` counter on the version, so a
  deleted reference stays retired even when it was the highest
- [x] 1.5 Rename `count_unresolved` → `count_open`; `DocumentSummary.unresolved` →
  `open_count`; `DocumentState.unresolved` → `open_comments`

## 2. API and CLI

- [x] 2.1 Remove the `/resolve` endpoint and its schemas
- [x] 2.2 Rename the state response field `unresolved` → `open_comments`
- [x] 2.3 Remove the `mdreview resolve` command
- [x] 2.4 Report: `OPEN:` header label, "open comments" section, revision
  instructions without the resolve step

## 3. Web

- [x] 3.1 Margin: replace Resolve with Edit (inline form) and Delete (confirmed)
  on open comments while commentable; show an "edited" marker
- [x] 3.2 Routes: POST `…/comments/{ref}/edit` and `…/comments/{ref}/delete`
  returning the sidebar; remove the resolve route
- [x] 3.3 Index chip counts open comments

## 4. Skill and docs

- [x] 4.1 Rewrite the requested-changes flow in `skill/md-review/SKILL.md`
  without the resolve step; update the sample report output
- [x] 4.2 Update README if it mentions resolve

## 5. Verification

- [x] 5.1 Migration test: a database created at schema 1 with a `resolved` row
  migrates to `outdated` with nothing lost
- [x] 5.2 Store tests: edit, delete, refusal on outdated, reference high-water mark
- [x] 5.3 Web tests: edit and delete forms, edited marker, escaping of edited bodies
- [x] 5.4 Update every test that used resolve or "unresolved"
- [x] 5.5 Full suite, ruff, screenshot harness
