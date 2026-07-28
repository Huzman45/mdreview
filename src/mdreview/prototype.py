"""PROTOTYPE — variant switching for the review page. Throwaway.

Three skins on the real /d/{slug} route, chosen with ?variant=A|B|C. Gated on
MDREVIEW_PROTOTYPE so the variants and the switcher cannot reach anyone by
accident; without it this module's `enabled()` is False and nothing changes.

Delete this file, the prototype templates, and the prototype stylesheets once a
variant has won.
"""

from __future__ import annotations

import os

ENV = "MDREVIEW_PROTOTYPE"

VARIANTS = {
    "A": "Editorial — margin comments",
    "B": "Glass — floating dock",
    "C": "Console — three panes",
}


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in {"1", "true", "yes"}


def resolve(requested: str | None) -> str | None:
    """The variant to render, or None to render the real page."""
    if not enabled() or not requested:
        return None
    key = requested.strip().upper()
    return key if key in VARIANTS else None


def context(current: str) -> dict[str, object]:
    keys = list(VARIANTS)
    index = keys.index(current)
    return {
        "variant": current,
        "variant_name": VARIANTS[current],
        "variant_keys": keys,
        "variant_prev": keys[(index - 1) % len(keys)],
        "variant_next": keys[(index + 1) % len(keys)],
    }
