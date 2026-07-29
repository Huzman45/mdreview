## 1. Storage

- [x] 1.1 Migration step 3: `documents.archived_at TEXT`
- [x] 1.2 `Document.archived_at`; `archive_document` (cancels a pending latest
  round in the same transaction), `unarchive_document`, `delete_document`
- [x] 1.3 `list_documents` filters by archived state; `submit` clears
  `archived_at` on resubmission

## 2. API and CLI

- [x] 2.1 `DELETE /api/documents/{slug}` → 204
- [x] 2.2 List endpoint gains an `archived` filter; pending filter covers
  active documents only
- [x] 2.3 `mdreview delete <slug>` with interactive confirmation and `--yes`

## 3. Web

- [x] 3.1 Row action: Archive on the index, Restore on the archived page;
  rows become wrappers so the button is not inside the link
- [x] 3.2 POST `/d/{slug}/archive` and `/d/{slug}/unarchive`, 303 back to the
  originating list
- [x] 3.3 `/archived` listing; foot-of-index count link shown only when
  non-empty

## 4. Verification

- [x] 4.1 Store tests: archive cancels pending, leaves decided alone, restore,
  resubmission reactivates, delete cascades
- [x] 4.2 API and CLI tests: delete endpoint, confirmation flow, filters
- [x] 4.3 Web tests: index excludes archived, archived page lists and
  restores, buttons post correctly
- [x] 4.4 Full suite, ruff, screenshot harness
