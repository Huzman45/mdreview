"""Process exit codes — the agent-facing contract.

An agent branches on these rather than on parsed text. Two of them carry most of
the design weight:

``PENDING`` exists so that "the human has not decided yet" can never be mistaken
for approval. In a hands-off loop the human often nudges the agent before
actually clicking anything, and an agent that reads "no changes requested" as
"approved" would implement an unreviewed plan.

``UNREACHABLE`` is kept distinct for the same reason: a dead server is an
infrastructure failure, not a review verdict.
"""

from __future__ import annotations

from enum import IntEnum

from .models import ReviewStatus


class Exit(IntEnum):
    OK = 0
    ERROR = 1
    CHANGES_REQUESTED = 2
    PENDING = 3
    CANCELLED = 4
    UNREACHABLE = 5


STATUS_EXIT: dict[ReviewStatus, Exit] = {
    ReviewStatus.APPROVED: Exit.OK,
    ReviewStatus.CHANGES_REQUESTED: Exit.CHANGES_REQUESTED,
    ReviewStatus.PENDING: Exit.PENDING,
    ReviewStatus.CANCELLED: Exit.CANCELLED,
}


def exit_for(status: ReviewStatus) -> Exit:
    return STATUS_EXIT[status]
