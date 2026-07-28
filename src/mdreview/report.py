"""Rendering review outcomes for an agent to read.

The audience is a language model, so the format optimises for being
unambiguous and self-contained: the status is on the first line, and every
comment carries the source text it refers to, so the agent never has to
re-read the document to understand the feedback.
"""

from __future__ import annotations

from typing import Any

from .models import ReviewStatus

QUOTE_PREFIX = "  > "
BODY_PREFIX = "  -> "

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


def header(status: ReviewStatus, version: int, open_count: int) -> str:
    return f"STATUS: {status.value}   VERSION: {version}   OPEN: {open_count}"


def comment_block(comment: dict[str, Any]) -> str:
    lines = [f"[{comment['ref']}] {line_label(comment)}"]
    for quoted in str(comment["quoted"]).splitlines() or [""]:
        lines.append(f"{QUOTE_PREFIX}{quoted}")
    for body in str(comment["body"]).splitlines():
        lines.append(f"{BODY_PREFIX}{body}")
    return "\n".join(lines)


def line_label(comment: dict[str, Any]) -> str:
    start, end = comment["line_start"], comment["line_end"]
    return f"L{start}" if start == end else f"L{start}-{end}"


def render_state(state: dict[str, Any]) -> str:
    """The full human- and agent-readable report for a document's latest version."""
    status = ReviewStatus(state["status"])
    open_comments = state.get("open_comments") or []
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
            parts.append(comment_block(comment))

    if status is ReviewStatus.CHANGES_REQUESTED:
        parts.append("")
        parts.append(REVISE_NOTE)

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
