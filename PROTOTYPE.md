# PROTOTYPE — three skins for the review page

**Throwaway.** Do not merge to `main` as-is. Delete or fold the winner in properly.

## The question

> The current interface is clean but generic. What should the review page actually
> look like?

Three variants on the **real** `/d/{slug}` route, with real documents, real
comments, real density — switchable with `?variant=A|B|C` and a floating bar.
Rendered on the live route on purpose: a variant judged in an empty vacuum always
looks fine, and the interesting failures only show up against a long document with
a wide table in it.

## The variants

Each disagrees about **structure**, not only palette. That is the point — otherwise
this is wallpaper, not a prototype.

| | Skin | Structural bet |
| --- | --- | --- |
| **A — Editorial** | Warm paper, serif headings, wide measure | Comments live in the **margin** beside the text they annotate, not in a right rail. Decision is a bar under the title. |
| **B — Glass** | Translucent layered panels over a gradient, blurred chrome | No sidebar at all. Comments open in a **slide-over sheet**; the decision sits in a **floating dock** at the bottom. |
| **C — Console** | Dense, monospace-forward, high contrast | **Three panes**: document outline on the left, text centre, comments as a **bottom console**. Keyboard-first. |

## How to run it

```bash
cd .worktrees/proto-ui-skins
MDREVIEW_PROTOTYPE=1 uv run mdreview serve --port 7500 --foreground
```

Then open any document and append the variant:

- <http://127.0.0.1:7500/d/treasury-ledgers?variant=A>
- <http://127.0.0.1:7500/d/treasury-ledgers?variant=B>
- <http://127.0.0.1:7500/d/treasury-ledgers?variant=C>

`←` / `→` cycle variants. Without `MDREVIEW_PROTOTYPE=1` the variants and the
switcher do not exist, so this cannot reach anyone by accident.

## Verdict

_To fill in._ The useful answer is usually not "B" but **"the header from B with
the outline from C"** — say that if it is what you think.

- Winner:
- Steal from the others:
- Reject outright:
