# Design

## D1. The assembly format is the contract

Each file contributes `# <path as written>`, a blank line, its content with
trailing whitespace normalised to one newline, then a blank line before the
next heading. Argument order is document order. The format is byte-for-byte
deterministic so a resubmission after edits diffs cleanly and an identical
resubmission stays an idempotent no-op (the store already guarantees the
latter on matching digests).

Paths appear exactly as the caller wrote them. Relative invocations give
readable headings; that is a calling convention for the skill to state, not
something the CLI rewrites. Rewriting (relativising, normalising) would make
the heading depend on where the command ran, which breaks determinism across
resubmissions from different directories.

## D2. Defaults come from the common parent, only for several files

`submit a.md b.md` with no `--slug` derives both slug and title from the
files' deepest common parent directory name (`add-multi-file-submit` →
`add-multi-file-submit`). One file keeps today's behaviour to the byte
(source name = file stem, title = first heading). Rationale: a file set is
almost always a directory's contents, and the directory name is the change
name; making the zero-option invocation correct is most of "ergonomic".
If the common parent is a filesystem root, submission proceeds with the
existing fallback (first heading) rather than failing.

## D3. Separation is generic part styling, not file awareness

The page styles any `<h1>` after the first as the opening of a new part
(space and a rule above). mdreview stays ignorant of openspec and of
assembly: a hand-written document with several top-level headings gets the
same treatment, which is consistent — in this design an `<h1>` *is* a part
boundary. No renderer or schema change.

## D4. Comment mapping lives in the report, keyed off the format

`review`/`await` fetch the decided version's content once and split it at
lines matching `^# (\S+)$` — the assembly format, applied in reverse. When
two or more such headings exist, each comment label gains its source:
`(design.md:12)`, ranges as `(design.md:12-15)`, and a comment on the
heading line itself as `(design.md, file heading)`. Otherwise the report is
unchanged. A single-token heading is not proof of assembly, so this is a
heuristic — but a false positive only adds an annotation that is still
true of the document's own structure.

The mapping is client-side so the server needs no concept of files. The
cost is one extra GET per report — never per poll; `await` polls `/state`
as before and fetches content only for its final report.

## D5. The content endpoint is plain and version-addressed

`GET /api/documents/{slug}/versions/{n}/content` returns the stored
markdown as `text/plain`. Version-addressed because reports are about a
specific version; plain text because the consumer wants bytes, not JSON
escaping. It also stands alone as a sensible API: agents resuming into a
review currently have no way to re-read what they submitted.

## D6. Failure modes stay quiet

If the content fetch fails (older server still running — the version-skew
warning already covers this), the report simply omits source annotations.
A mapping must never be the reason an agent cannot read its outcome.
