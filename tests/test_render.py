"""Anchoring is the part most likely to harbour subtle bugs, so it is tested hard."""

from __future__ import annotations

import pytest

from mdreview import render
from mdreview.render import Block

PLAN = """# Migration plan

Intro paragraph
wrapping two lines.

- first bullet
- second bullet
- third bullet

```sql
SELECT 1;
```

| a | b |
| - | - |
| 1 | 2 |

> a quoted aside

---
"""


def blocks_of(content: str) -> tuple[Block, ...]:
    return render.render(content).blocks


def test_every_block_kind_is_addressable() -> None:
    kinds = [b.kind for b in blocks_of(PLAN)]
    assert "heading_open" in kinds
    assert "paragraph_open" in kinds
    assert "fence" in kinds
    assert "table_open" in kinds
    assert "blockquote_open" in kinds
    assert "hr" in kinds


def test_each_list_item_is_separately_addressable() -> None:
    items = [b for b in blocks_of(PLAN) if b.kind == "list_item_open"]
    assert len(items) == 3
    # Distinct, non-overlapping ranges — one per bullet.
    assert len({(b.line_start, b.line_end) for b in items}) == 3


def test_paragraphs_inside_list_items_are_not_double_anchored() -> None:
    """The item is the anchor; anchoring its inner paragraph too would nest
    two click targets over identical text."""
    content = "- only bullet\n"
    kinds = [b.kind for b in blocks_of(content)]
    assert kinds == ["list_item_open"]


def test_paragraphs_inside_blockquotes_are_not_double_anchored() -> None:
    content = "> quoted\n"
    kinds = [b.kind for b in blocks_of(content)]
    assert kinds == ["blockquote_open"]


def test_ranges_are_one_based_and_inclusive() -> None:
    content = "# Title\n\nBody line\n"
    blocks = blocks_of(content)
    heading = blocks[0]
    assert (heading.line_start, heading.line_end) == (1, 1)
    body = blocks[1]
    assert (body.line_start, body.line_end) == (3, 3)


def test_ranges_stay_within_the_document() -> None:
    total = render.line_count(PLAN)
    for block in blocks_of(PLAN):
        assert 1 <= block.line_start <= block.line_end <= total


def test_every_range_round_trips_to_its_source() -> None:
    for block in blocks_of(PLAN):
        quoted = render.quote_lines(PLAN, block.line_start, block.line_end)
        assert quoted.strip(), f"{block.kind} produced an empty quote"
        # The quoted text must actually appear in the document.
        assert quoted in PLAN


def test_a_heading_range_quotes_exactly_that_heading() -> None:
    blocks = blocks_of(PLAN)
    heading = next(b for b in blocks if b.kind == "heading_open")
    assert render.quote_lines(PLAN, heading.line_start, heading.line_end) == "# Migration plan"


def test_a_bullet_range_quotes_exactly_that_bullet() -> None:
    items = [b for b in blocks_of(PLAN) if b.kind == "list_item_open"]
    quoted = render.quote_lines(PLAN, items[1].line_start, items[1].line_end)
    assert quoted.strip() == "- second bullet"


def test_html_carries_the_line_attributes() -> None:
    html = render.render("# Title\n").html
    assert 'data-line-start="1"' in html
    assert 'data-line-end="1"' in html
    assert render.ANCHOR_CLASS in html


def test_list_items_are_not_wrapped_in_invalid_markup() -> None:
    """Attributes go on the <li> itself; a wrapper div there would be invalid."""
    html = render.render("- one\n- two\n").html
    assert "<li" in html
    assert "<div" not in html


def test_code_fences_are_anchored_on_a_wrapper_not_the_inner_code() -> None:
    """markdown-it puts token attributes on <code>, which would leave the
    padding of the surrounding <pre> unclickable."""
    html = render.render("```sql\nSELECT 1;\n```\n").html
    assert f'<div class="{render.ANCHOR_CLASS}" data-line-start="1"' in html
    assert "<code" in html
    # The anchor must not have landed on the inner element.
    assert 'code class="mdr-block"' not in html
    assert "<code data-line-start" not in html


def test_fence_content_is_not_mangled_by_wrapping() -> None:
    html = render.render("```python\ndef f():\n    return 1\n```\n").html
    assert "def f():\n    return 1\n" in html


def test_indented_code_blocks_are_anchored_too() -> None:
    blocks = blocks_of("    indented code\n")
    assert [b.kind for b in blocks] == ["code_block"]


# -- untrusted input --------------------------------------------------------


def test_script_tags_render_as_text() -> None:
    html = render.render("<script>alert(1)</script>\n").html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_inline_event_handlers_render_as_text() -> None:
    html = render.render('<div onclick="steal()">hi</div>\n').html
    # The tag is neutralised: it survives only as escaped text, never as an
    # element that could carry a live handler.
    assert "<div" not in html
    assert 'onclick="steal()"' not in html
    assert "&lt;div onclick=&quot;steal()&quot;&gt;" in html


def test_javascript_link_targets_never_reach_an_href() -> None:
    """A rejected link degrades to inert literal text, not an anchor element.

    The scheme still appears in the output as escaped prose, which is harmless;
    what matters is that no <a> is emitted for it.
    """
    html = render.render("[click](javascript:alert(1))\n").html
    assert "<a " not in html
    assert 'href="javascript:' not in html


def test_data_uri_link_targets_never_reach_an_href() -> None:
    html = render.render("[x](data:text/html;base64,PHNjcmlwdD4=)\n").html
    assert "<a " not in html
    assert 'href="data:' not in html


def test_a_rejected_link_is_escaped_when_it_degrades_to_text() -> None:
    html = render.render('[x](javascript:alert("<b>"))\n').html
    assert "<b>" not in html


def test_ordinary_links_survive() -> None:
    html = render.render("[ok](https://example.com)\n").html
    assert 'href="https://example.com"' in html


@pytest.mark.parametrize(
    "url",
    ["https://e.com", "http://e.com", "mailto:a@e.com", "/relative", "#anchor"],
)
def test_allowed_link_schemes(url: str) -> None:
    assert render._validate_link(url)


@pytest.mark.parametrize("url", ["javascript:x", "vbscript:x", "data:text/html,x"])
def test_rejected_link_schemes(url: str) -> None:
    assert not render._validate_link(url)


# -- quoting ----------------------------------------------------------------


def test_quote_lines_extracts_an_inclusive_range() -> None:
    content = "one\ntwo\nthree\nfour\n"
    assert render.quote_lines(content, 2, 3) == "two\nthree"


def test_quote_lines_rejects_an_out_of_bounds_range() -> None:
    with pytest.raises(ValueError, match="outside a document"):
        render.quote_lines("one\ntwo\n", 1, 99)


def test_quote_lines_rejects_an_inverted_range() -> None:
    with pytest.raises(ValueError):
        render.quote_lines("one\ntwo\n", 2, 1)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [(1, 1, True), (1, 2, True), (0, 1, False), (1, 3, False), (2, 1, False)],
)
def test_is_within(start: int, end: int, expected: bool) -> None:
    assert render.is_within("one\ntwo\n", start, end) is expected


def test_empty_document_has_no_blocks() -> None:
    assert blocks_of("") == ()
