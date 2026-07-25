"""Markdown rendering with source-line anchoring.

This module is pure: content in, HTML and block ranges out. The anchoring logic
is the part of the system most likely to harbour subtle bugs, so it is kept
free of any dependency on a database or a server.

Anchors work because ``markdown-it-py`` reports the source line range that
produced each block token. Since a version's bytes are immutable, a range
recorded against it stays valid forever — which is why comments in this tool can
never drift onto the wrong text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.tasklists import tasklists_plugin

#: Schemes a link may use. Anything else is stripped, so a document cannot
#: smuggle in a ``javascript:`` payload. markdown-it already rejects these by
#: default; the allow-list makes the guarantee explicit rather than inherited.
ALLOWED_SCHEMES = frozenset({"http", "https", "mailto", "ftp", ""})

#: Block tokens that become comment targets when they appear at the top level.
TOP_LEVEL_ANCHORS = frozenset(
    {
        "heading_open",
        "paragraph_open",
        "blockquote_open",
        "fence",
        "code_block",
        "table_open",
        "hr",
        "html_block",
    }
)

#: Fences render as ``<pre><code>``, and markdown-it puts token attributes on
#: the inner ``<code>``. Anchoring there would leave the surrounding padding of
#: the ``<pre>`` unclickable, which is a poor target for what is often the most
#: commented-on element in a plan. These are wrapped in an anchored ``div``
#: instead — valid around a ``<pre>``, unlike around a ``<li>``.
WRAPPED_ANCHORS = frozenset({"fence", "code_block"})

#: Anchored at any depth, so that feedback can target one bullet of a list —
#: which is what most review comments on a plan actually address.
NESTED_ANCHORS = frozenset({"list_item_open"})

ANCHOR_CLASS = "mdr-block"


@dataclass(frozen=True, slots=True)
class Block:
    """An addressable region of a document.

    Lines are 1-based and inclusive, matching how a reviewer refers to them,
    rather than the 0-based half-open ranges markdown-it reports internally.
    """

    line_start: int
    line_end: int
    kind: str


@dataclass(frozen=True, slots=True)
class Rendered:
    html: str
    blocks: tuple[Block, ...]


def _validate_link(url: str) -> bool:
    try:
        scheme = urlparse(url).scheme.lower()
    except ValueError:
        return False
    return scheme in ALLOWED_SCHEMES


def _anchored(original: Callable[..., str]) -> Callable[..., str]:
    """Wrap a render rule's output in an anchored ``div``."""

    def rule(tokens: list[Token], idx: int, options: object, env: object) -> str:
        inner = original(tokens, idx, options, env)
        token = tokens[idx]
        if token.map is None:
            return inner
        start, end = token.map
        return (
            f'<div class="{ANCHOR_CLASS}" data-line-start="{start + 1}"'
            f' data-line-end="{end}">{inner}</div>'
        )

    return rule


def build_parser() -> MarkdownIt:
    """A parser that treats its input as hostile.

    ``html=False`` makes embedded markup render as visible text instead of
    active HTML, which matters because document content comes from an agent and
    is therefore untrusted.
    """
    md = MarkdownIt("default", {"html": False, "linkify": False, "typographer": False})
    md.validateLink = _validate_link
    # Task lists render as real checkboxes. They stay disabled: the agent owns
    # the file, so nothing on the page may edit a document about to be revised.
    md.use(tasklists_plugin, enabled=False)
    for name in WRAPPED_ANCHORS:
        original = md.renderer.rules.get(name) or getattr(md.renderer, name)
        md.renderer.rules[name] = _anchored(original)
    return md


def _is_anchor(token: Token) -> bool:
    if token.map is None:
        return False
    if token.type in NESTED_ANCHORS:
        return True
    return token.level == 0 and token.type in TOP_LEVEL_ANCHORS


def render(content: str, *, parser: MarkdownIt | None = None) -> Rendered:
    """Render ``content``, tagging every addressable block with its line range.

    Attributes are set on the tokens themselves rather than wrapping the output
    in extra elements, so the emitted HTML stays valid — a wrapper ``div``
    around a list item would not be.
    """
    md = parser or build_parser()
    tokens = md.parse(content)

    blocks: list[Block] = []

    for token in tokens:
        if not _is_anchor(token):
            continue
        assert token.map is not None  # narrowed by _is_anchor
        start, end = token.map
        blocks.append(Block(line_start=start + 1, line_end=end, kind=token.type))

        # Wrapped kinds are handled by their render rule, which reads token.map
        # directly. Setting attributes here would put them on the inner element.
        if token.type in WRAPPED_ANCHORS:
            continue

        token.attrSet("data-line-start", str(start + 1))
        token.attrSet("data-line-end", str(end))
        existing = token.attrGet("class")
        token.attrSet(
            "class", f"{existing} {ANCHOR_CLASS}".strip() if existing else ANCHOR_CLASS
        )

    html = md.renderer.render(tokens, md.options, {})
    return Rendered(html=html, blocks=tuple(blocks))


def line_count(content: str) -> int:
    return len(content.splitlines())


def quote_lines(content: str, line_start: int, line_end: int) -> str:
    """Extract the markdown source for a 1-based inclusive line range."""
    lines = content.splitlines()
    if line_start < 1 or line_end < line_start or line_end > len(lines):
        raise ValueError(
            f"line range {line_start}-{line_end} is outside a document of {len(lines)} lines"
        )
    return "\n".join(lines[line_start - 1 : line_end])


def is_within(content: str, line_start: int, line_end: int) -> bool:
    return 1 <= line_start <= line_end <= line_count(content)
