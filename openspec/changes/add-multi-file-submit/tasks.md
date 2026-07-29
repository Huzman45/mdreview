- [x] `cli.py`: `submit` takes one or more paths; `_assemble` builds the
      deterministic bundle; slug/title default from the common parent for
      several files; single-file behaviour unchanged.
- [x] `api.py`: `GET /documents/{slug}/versions/{n}/content` returning
      `text/plain`.
- [x] `report.py`: split content at assembly headings; annotate comment
      labels with `path:line`; omit annotations when content is missing or
      headings are absent.
- [x] `cli.py`: `review`/`await` fetch content for the final report and pass
      it to the renderer; fetch failures degrade to the unannotated report.
- [x] `app.css`: part separation for `h1`s after the first.
- [x] Tests: assembly determinism and ordering; heading injection; parent-
      derived defaults; single-file unchanged; idempotent resubmission of a
      bundle; content endpoint; mapping labels (single line, range, heading
      line, no-heading fallback, fetch-failure fallback).
- [x] `skill/md-review/SKILL.md`: "Reviewing a set of files" section.
- [x] `.opencode/commands/opsx-propose.md`: end by submitting the bundle.
