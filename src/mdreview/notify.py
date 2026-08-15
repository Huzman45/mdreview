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

    Returns as soon as the delivery thread is running, never later: the caller
    is a request handler whose reviewer is waiting on a button. Spawning is
    itself guarded, because a handler that raised here would fail a decision
    that is already recorded — the outcome this module exists to prevent.

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
    """Post once and forget the outcome, including a failed one.

    There is no caller left to return an error to and, by design, no retry to
    schedule. `trust_env` is deliberately left on, unlike the CLI's client: that
    one refuses proxies because it may only ever reach loopback, whereas a
    webhook points wherever the operator's listener is.
    """
    with contextlib.suppress(Exception):
        httpx.post(url, json=payload, timeout=TIMEOUT)
