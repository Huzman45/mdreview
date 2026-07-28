"""Screenshot every page type, at every width, in both colour schemes.

Used to review the interface while changing it. Kept in the repo because the
alternative is re-deriving the same viewport list by hand every time, and because
the overflow check below catches the single most common regression: something
wider than the screen on a narrow device.

    uv run python scripts/shots.py [--out DIR] [--base URL]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# One representative document per page type. Chosen to have several versions, so
# the diff view has something to show.
VIEWS = [
    ("index", "/"),
    ("rendered", "/d/{slug}"),
    ("raw", "/d/{slug}/v/{version}/raw"),
    ("diff", "/d/{slug}/diff/{previous}/{version}"),
]

# phone, iPad portrait, iPad landscape, laptop
SIZES = [
    ("phone", 390, 844),
    ("ipad", 834, 1194),
    ("ipad-wide", 1194, 834),
    ("desktop", 1440, 900),
]

THEMES = ("light", "dark")


def capture(
    base: str, out: Path, slug: str, version: int, previous: int
) -> list[dict[str, object]]:
    out.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for theme in THEMES:
                for size_name, width, height in SIZES:
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=2,
                    )
                    page = context.new_page()
                    # Seed the stored preference before any page script runs.
                    seed = (
                        "try { localStorage.setItem('mdreview-theme', "
                        f"'{theme}'); }} catch (e) {{}}"
                    )
                    page.add_init_script(seed)
                    for view_name, template in VIEWS:
                        path = template.format(slug=slug, version=version, previous=previous)
                        page.goto(base + path, wait_until="domcontentloaded")
                        page.wait_for_timeout(900)

                        name = f"{theme}-{size_name}-{view_name}.png"
                        page.screenshot(path=str(out / name), full_page=False)

                        overflow = page.evaluate(
                            "() => document.documentElement.scrollWidth"
                            " - document.documentElement.clientWidth"
                        )
                        applied = page.get_attribute("html", "data-theme")
                        findings.append(
                            {
                                "shot": name,
                                "overflow": overflow,
                                "theme": applied,
                                "ok": overflow == 0 and applied == theme,
                            }
                        )
                    context.close()
        finally:
            browser.close()
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:7391")
    parser.add_argument("--out", default=".shots")
    parser.add_argument("--slug", default="treasury-ledgers")
    parser.add_argument("--version", type=int, default=2)
    parser.add_argument("--previous", type=int, default=1)
    args = parser.parse_args()

    findings = capture(args.base, Path(args.out), args.slug, args.version, args.previous)
    bad = [f for f in findings if not f["ok"]]
    print(json.dumps({"captured": len(findings), "problems": bad}, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
