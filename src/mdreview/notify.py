"""Announcing a recorded decision to an endpoint outside the review loop.

`mdreview await` already tells the agent that submitted a document how its own
review went. This is for everything else that cares — a chat notifier, a CI
trigger, a dashboard — none of which wants to poll every document on a timer to
observe an event that happens a few times a day.

Recording the decision is the job; announcing it is strictly secondary, and the
code is arranged so that it can never become the other way round.
"""

from __future__ import annotations

import contextlib
import threading
from typing import Any

import httpx

TIMEOUT = 5.0


def fire_decision(
    url: str | None,
    *,
    slug: str,
    version: int,
    status: str,
    note: str | None,
    decided_at: str | None,
) -> None:
    """Announce a decision that has already been committed.

    Returns the moment the delivery thread is running, never later: the caller
    is a request handler whose reviewer is waiting on a button, and no listener
    gets to make them wait longer. Spawning is itself guarded, because a
    handler that raised here would fail a decision that is already recorded —
    the one outcome this whole module exists to prevent.

    The payload carries the decision's own facts so a consumer can act on the
    event directly; the state endpoint stays authoritative for anything more.
    """
    if not url:
        return
    payload = {
        "slug": slug,
        "version": version,
        "status": status,
        "note": note,
        "decided_at": decided_at,
    }
    with contextlib.suppress(Exception):
        threading.Thread(target=_deliver, args=(url, payload), daemon=True).start()


def _deliver(url: str, payload: dict[str, Any]) -> None:
    """Post once, and forget the outcome including a failed one.

    Nothing here has anything useful to do with an error: there is no caller
    left to return it to and, by design, no retry to schedule. The timeout is
    the only thing that matters, and only so that an unresponsive listener
    releases the thread rather than pinning it.

    Unlike the CLI's client this one leaves `trust_env` alone. That client
    refuses proxies because it may only ever talk to loopback; a webhook points
    wherever the operator's listener actually is, which may be through one.
    """
    with contextlib.suppress(Exception):
        httpx.post(url, json=payload, timeout=TIMEOUT)
