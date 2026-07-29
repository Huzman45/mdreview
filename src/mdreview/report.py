"""Rendering review outcomes for an agent to read.

The audience is a language model, so the format optimises for being
unambiguous and self-contained: the status is on the first line, and every
comment carries the source text it refers to, so the agent never has to
re-read the document to understand the feedback. When the document was
assembled from several files, each comment also names the file and
file-local line it lands in, so the agent edits the right file without
doing the arithmetic itself.
"""

from __future__ import annotations

import re
from typing import Any

from .models import ReviewStatus

QUOTE_PREFIX = "  > "
BODY_PREFIX = "  -> "

#: The multi-file assembly format, applied in reverse: `submit a.md b.md ...`
#: opens each file with `# <path>`, so two or more such headings identify a
#: document whose comment ranges can be traced back to source files.
ASSEMBLY_HEADING = re.compile(r"^# (\S+)$")

PENDING_NOTE = (
    "No decision has been recorded yet. Do not proceed as though this were "
    "approved; tell the user the review is still outstanding."
)

CANCELLED_NOTE = "This review was cancelled. Stop and ask the user how to proceed."

REVISE_NOTE = (
    "Address each comment, then resubmit the revised file with "
    "'mdreview submit <file> --slug <slug>' for another round. Resubmitting "
    "supersedes these comments; there is nothing to mark as done."
)

REVISE_NOTE_ASSEMBLED = (
    "Fix each comment in the source file its label names, then resubmit the "
    "same files in the same order with 'mdreview submit <files...> --slug "
    "<slug>' for another round. Resubmitting supersedes these comments; "
    "there is nothing to mark as done."
)


def header(status: ReviewStatus, version: int, open_count: int) -> str:
    return f"STATUS: {status.value}   VERSION: {version}   OPEN: {open_count}"


def section_marks(content: str | None) -> list[tuple[int, str]]:
    """``(heading_line, path)`` pairs when the content looks assembled.

    Fewer than two assembly headings is an ordinary document: a single
    `# token` heading is far more likely to be a title than a bundle of one.
    """
    if not content:
        return []
    marks = [
        (i, m.group(1))
        for i, line in enumerate(content.splitlines(), start=1)
        if (m := ASSEMBLY_HEADING.match(line))
    ]
    return marks if len(marks) >= 2 else []


def source_label(marks: list[tuple[int, str]], start: int, end: int) -> str | None:
    """Where a document line range falls, in file-local terms."""
    prior = [mark for mark in marks if mark[0] <= start]
    if not prior:
        return None
    heading_line, path = prior[-1]
    # The assembler writes `# <path>`, one blank line, then the file, so the
    # file's own line 1 sits two below its heading.
    local_start = start - heading_line - 1
    local_end = end - heading_line - 1
    if local_start < 1:
        return f"{path}, file heading"
    if start == end:
        return f"{path}:{local_start}"
    return f"{path}:{local_start}-{local_end}"


def comment_block(comment: dict[str, Any], marks: list[tuple[int, str]] | None = None) -> str:
    label = line_label(comment)
    source = source_label(marks or [], comment["line_start"], comment["line_end"])
    if source:
        label = f"{label} ({source})"
    lines = [f"[{comment['ref']}] {label}"]
    for quoted in str(comment["quoted"]).splitlines() or [""]:
        lines.append(f"{QUOTE_PREFIX}{quoted}")
    for body in str(comment["body"]).splitlines():
        lines.append(f"{BODY_PREFIX}{body}")
    return "\n".join(lines)


def line_label(comment: dict[str, Any]) -> str:
    start, end = comment["line_start"], comment["line_end"]
    return f"L{start}" if start == end else f"L{start}-{end}"


def render_state(state: dict[str, Any], content: str | None = None) -> str:
    """The full human- and agent-readable report for a document's latest version.

    ``content`` is the reviewed version's markdown when the caller could
    fetch it; without it the report is simply rendered unannotated.
    """
    status = ReviewStatus(state["status"])
    open_comments = state.get("open_comments") or []
    marks = section_marks(content)
    parts = [header(status, state["version"], len(open_comments))]

    note = state.get("decision_note")
    if note:
        parts.append(f"NOTE: {note}")

    if status is ReviewStatus.PENDING:
        parts.append("")
        parts.append(PENDING_NOTE)
        parts.append(f"Review at: {state['url']}")
    elif status is ReviewStatus.CANCELLED:
        parts.append("")
        parts.append(CANCELLED_NOTE)

    if open_comments:
        parts.append("")
        parts.append(f"--- open comments ({len(open_comments)}) ---")
        for comment in open_comments:
            parts.append("")
            parts.append(comment_block(comment, marks))

    if status is ReviewStatus.CHANGES_REQUESTED:
        parts.append("")
        parts.append(REVISE_NOTE_ASSEMBLED if marks else REVISE_NOTE)

    return "\n".join(parts)


def render_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No documents."
    width = max(len(item["slug"]) for item in items)
    lines = []
    for item in items:
        slug = item["slug"].ljust(width)
        project = item.get("project_path") or "-"
        lines.append(
            f"{slug}  v{item['version']}  {item['status']:<18}  {item['title']}"
            f"\n{' ' * width}  {project}"
        )
    return "\n".join(lines)
