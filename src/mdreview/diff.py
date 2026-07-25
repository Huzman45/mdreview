"""Line differences between two versions.

Pure: content in, typed rows out. No database, no HTTP, so the classification
logic is testable on its own.

A unified diff rather than side-by-side, because side-by-side is unreadable at
phone width and this tool is used from a phone.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum

#: Unchanged lines kept either side of a change, for orientation. Printing the
#: whole document would bury small revisions in noise.
DEFAULT_CONTEXT = 3


class RowKind(StrEnum):
    CONTEXT = "context"
    ADDED = "added"
    REMOVED = "removed"
    SKIP = "skip"
    """A gap where unchanged lines were omitted."""


@dataclass(frozen=True, slots=True)
class Row:
    kind: RowKind
    text: str
    old_line: int | None = None
    new_line: int | None = None

    @property
    def marker(self) -> str:
        return {
            RowKind.ADDED: "+",
            RowKind.REMOVED: "-",
            RowKind.CONTEXT: " ",
            RowKind.SKIP: "",
        }[self.kind]


@dataclass(frozen=True, slots=True)
class Diff:
    rows: tuple[Row, ...]
    added: int
    removed: int

    @property
    def is_empty(self) -> bool:
        return self.added == 0 and self.removed == 0


def compare(old: str, new: str, *, context: int = DEFAULT_CONTEXT) -> Diff:
    """Compare two document versions line by line."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    matcher = SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)

    rows: list[Row] = []
    added = 0
    removed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows.extend(_context_rows(old_lines, i1, i2, j1, context))
            continue
        if tag in {"replace", "delete"}:
            for offset, line in enumerate(old_lines[i1:i2]):
                rows.append(Row(RowKind.REMOVED, line, old_line=i1 + offset + 1))
                removed += 1
        if tag in {"replace", "insert"}:
            for offset, line in enumerate(new_lines[j1:j2]):
                rows.append(Row(RowKind.ADDED, line, new_line=j1 + offset + 1))
                added += 1

    if added == 0 and removed == 0:
        rows = []

    return Diff(rows=tuple(rows), added=added, removed=removed)


def _context_rows(old_lines: list[str], i1: int, i2: int, j1: int, context: int) -> list[Row]:
    """Context around a change, with a gap marker when lines are omitted."""
    length = i2 - i1
    at_start = i1 == 0
    at_end = i2 == len(old_lines)

    def row(index: int) -> Row:
        return Row(
            RowKind.CONTEXT,
            old_lines[index],
            old_line=index + 1,
            new_line=j1 + (index - i1) + 1,
        )

    # Short enough to show whole.
    if length <= context * 2:
        return [row(i) for i in range(i1, i2)]

    head = [] if at_start else [row(i) for i in range(i1, i1 + context)]
    tail = [] if at_end else [row(i) for i in range(i2 - context, i2)]
    omitted = length - len(head) - len(tail)
    gap = [Row(RowKind.SKIP, f"{omitted} unchanged lines")] if omitted > 0 else []
    return head + gap + tail
