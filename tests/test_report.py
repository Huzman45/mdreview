from __future__ import annotations

from mdreview import report
from mdreview.models import ReviewStatus

COMMENT = {
    "ref": "C1",
    "line_start": 12,
    "line_end": 14,
    "quoted": "## Phase 2\nmigrate in one shot",
    "body": "split this per tenant",
    "state": "open",
}


def state(**overrides: object) -> dict:
    base = {
        "slug": "plan",
        "title": "Plan",
        "project_path": "/tmp/p",
        "version": 2,
        "status": "changes_requested",
        "decision_note": None,
        "decided_at": None,
        "url": "http://127.0.0.1:7391/d/plan",
        "open_comments": [COMMENT],
    }
    base.update(overrides)
    return base


def test_header_leads_with_the_status() -> None:
    text = report.render_state(state())
    assert text.splitlines()[0] == "STATUS: changes_requested   VERSION: 2   OPEN: 1"


def test_comment_includes_reference_range_quote_and_body() -> None:
    text = report.render_state(state())
    assert "[C1] L12-14" in text
    assert "  > ## Phase 2" in text
    assert "  > migrate in one shot" in text
    assert "  -> split this per tenant" in text


def test_single_line_ranges_are_not_written_as_a_span() -> None:
    comment = {**COMMENT, "line_start": 7, "line_end": 7}
    text = report.render_state(state(open_comments=[comment]))
    assert "[C1] L7\n" in text
    assert "L7-7" not in text


def test_pending_says_no_decision_was_recorded() -> None:
    text = report.render_state(state(status="pending", open_comments=[]))
    assert "No decision has been recorded yet" in text
    assert "Do not proceed" in text
    assert "http://127.0.0.1:7391/d/plan" in text


def test_pending_header_reports_zero_open() -> None:
    text = report.render_state(state(status="pending", open_comments=[]))
    assert text.splitlines()[0].endswith("OPEN: 0")


def test_approved_is_terse() -> None:
    text = report.render_state(state(status="approved", open_comments=[]))
    assert text.splitlines()[0].startswith("STATUS: approved")
    assert "open comments" not in text


def test_cancelled_tells_the_agent_to_stop() -> None:
    text = report.render_state(state(status="cancelled", open_comments=[]))
    assert "Stop and ask the user" in text


def test_changes_requested_explains_the_next_step() -> None:
    text = report.render_state(state())
    assert "resubmit" in text
    assert "--slug" in text
    assert "resolve" not in text


def test_a_decision_note_is_surfaced() -> None:
    text = report.render_state(state(decision_note="too risky"))
    assert "NOTE: too risky" in text


def test_multiple_comments_are_all_rendered() -> None:
    second = {**COMMENT, "ref": "C2", "line_start": 30, "line_end": 30}
    text = report.render_state(state(open_comments=[COMMENT, second]))
    assert "OPEN: 2" in text
    assert "[C1]" in text
    assert "[C2]" in text


def test_header_helper() -> None:
    assert report.header(ReviewStatus.APPROVED, 3, 0) == (
        "STATUS: approved   VERSION: 3   OPEN: 0"
    )


def test_render_list_is_readable() -> None:
    items = [
        {
            "slug": "plan",
            "title": "Migration plan",
            "version": 2,
            "status": "pending",
            "project_path": "/tmp/sapphire",
        }
    ]
    text = report.render_list(items)
    assert "plan" in text
    assert "v2" in text
    assert "pending" in text
    assert "/tmp/sapphire" in text


def test_render_list_handles_nothing() -> None:
    assert report.render_list([]) == "No documents."


# -- source mapping for assembled documents ----------------------------------

ASSEMBLED = (
    "# proposal.md\n\nWhy we do this.\n\nMore why.\n\n"   # heading L1, content L3-5
    "# specs/agent-cli/spec.md\n\nA requirement.\nA scenario.\n"  # heading L7
)


def test_section_marks_need_two_headings() -> None:
    assert report.section_marks("# title.md\n\nBody.\n") == []
    assert report.section_marks(None) == []
    assert report.section_marks("# Plain Title\n\n# another one\n") == []


def test_section_marks_find_assembly_headings() -> None:
    assert report.section_marks(ASSEMBLED) == [
        (1, "proposal.md"),
        (7, "specs/agent-cli/spec.md"),
    ]


def test_source_label_maps_lines_ranges_and_headings() -> None:
    marks = report.section_marks(ASSEMBLED)
    # Assembly line 3 is "Why we do this." — line 1 of proposal.md itself.
    assert report.source_label(marks, 3, 3) == "proposal.md:1"
    assert report.source_label(marks, 9, 10) == "specs/agent-cli/spec.md:1-2"
    assert report.source_label(marks, 7, 7) == "specs/agent-cli/spec.md, file heading"


def test_render_state_annotates_comments_with_their_source() -> None:
    comment = {**COMMENT, "line_start": 9, "line_end": 9}
    output = report.render_state(state(open_comments=[comment]), ASSEMBLED)
    assert "[C1] L9 (specs/agent-cli/spec.md:1)" in output
    assert "same files in the same order" in output


def test_render_state_without_content_is_unannotated() -> None:
    output = report.render_state(state())
    assert "(proposal.md" not in output
    assert "[C1] L12-14" in output
    assert report.REVISE_NOTE in output
