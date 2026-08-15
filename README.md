# mdreview

Review agent-authored markdown in a browser instead of a text editor.

An AI coding agent writes a plan to `PLAN.md` and runs `mdreview submit PLAN.md`.
A browser tab opens with the rendered markdown. You comment on individual
headings, paragraphs, bullets or code blocks, then hit **Approve** or **Request
changes**. The agent reads your decision and your comments back with
`mdreview review` and carries on.

Local-first. Single user. No auth, no cloud, no daemon. Private-LAN access is
available as an explicit opt-in for reviewing from a phone.

## Why

Reviewing an agent's plan currently means opening an editor, reading raw
markdown, and describing feedback in prose — "change the bit on line 5, and also
line 10". The feedback gets detached from the text it refers to, the agent has to
guess which passage you meant, and there is no record of what was agreed.

## Install

```bash
git clone git@github.com:fjvillamarin/mdreview.git
cd mdreview
uv sync
```

Then install the CLI and the agent skill together:

```bash
mise run setup
```

That does three things:

- `install-cli` — `uv tool install --editable .`, putting `mdreview` on your
  `PATH`. Editable means the command tracks this checkout, so **the tool breaks
  if you move or delete this directory**. Drop `--editable` if you would rather
  have a copy that survives that, at the cost of reinstalling to pick up changes.
- `install-skill` — copies `skill/md-review` to `~/.agents/skills/md-review` and
  symlinks it into `~/.claude/skills/`, so opencode and Claude Code both see one
  source of truth. Re-run it after editing the skill.
- `install-opencode-plugin` — copies `contrib/opencode/mdreview-session.js` to
  `~/.config/opencode/plugins/`. opencode does not expose its session id to
  shell commands the way Claude Code does; the plugin injects
  `OPENCODE_SESSION_ID` per command so a submission records which conversation
  it came from. Without it, opencode submissions still record the tool, just
  not the session.

Each submission records where it came from: the project directory and, when
detectable, the agent session. Detection reads the environment at submit time —
`MDREVIEW_SESSION_ID` (explicit override) first, then `OPENCODE_SESSION_ID`
(injected per command by the plugin above), then `CLAUDE_CODE_SESSION_ID`
(exported by Claude Code), then the bare `OPENCODE`/`CLAUDECODE` presence
markers, which record the tool without an id.

Optionally, add this to your global agent instructions so agents reach for it by
default rather than pasting plans into chat:

```markdown
## Plan review

When you produce a plan, design or proposal for me to approve, do not paste it
into chat. Write it to a markdown file and publish it with `mdreview submit`,
tell me the URL, and stop. When I say the review is done, run
`mdreview review <slug>` first and branch on the exit code.
```

## Use

```bash
mdreview submit PLAN.md          # publish, open the browser, print the URL
mdreview review plan             # read the outcome; the exit code is the answer
mdreview await plan              # wait for the outcome (made to run in background)
mdreview list --pending          # what is awaiting a decision
mdreview status plan             # one-line summary
mdreview open plan               # reopen the page
mdreview serve                   # run the server explicitly (rarely needed)
```

### Exit codes

`mdreview review` communicates the outcome through its exit status, so an agent
can branch on it without parsing text.

| Code | Meaning | Agent action |
| ---- | ------- | ------------ |
| 0 | `approved` | Proceed |
| 2 | `changes_requested` | Address comments, resubmit |
| 3 | `pending` — no decision recorded | Report and wait; **do not** proceed |
| 4 | `cancelled` | Stop and ask |
| 5 | API unreachable | Infrastructure failure, not a verdict |

Code 3 is the important one. In a hands-off loop you will sometimes nudge the
agent before you have actually clicked anything, and an agent that reads "no
changes requested" as "approved" would implement an unreviewed plan.

`mdreview await` closes the loop without the nudge: it polls until a decision
lands, then exits with the same code and report as `review`. An agent whose
harness supports background tasks starts it after submitting and is woken by
its completion — nobody has to type "done". It times out (default eight
hours) with exit 3, and a server that never answers is exit 5, never a
verdict.

### Output shape

`review` renders feedback for a language model to act on without re-reading the
file:

```
STATUS: changes_requested   VERSION: 1   OPEN: 2

--- open comments (2) ---

[C1] L12-14
  > ## Phase 2: migrate the table in one shot
  -> split this per tenant, we cannot hold the lock that long

[C2] L30
  > wrap the migration in a transaction
  -> BigQuery has no DDL transactions
```

## Agent instructions snippet

Paste into your `AGENTS.md` or `CLAUDE.md`:

```markdown
## Plan review

When you produce a plan, design or proposal for me to approve, do not paste it
into chat. Write it to a markdown file and publish it:

    mdreview submit PLAN.md

Tell me the URL and stop — do not start implementing. When I say the review is
done, run `mdreview review <slug>` as your first action and branch on the exit
code: 0 proceed, 2 address the comments and resubmit, 3 the review is still
outstanding so keep waiting, 4 stop and ask.
```

## The review page

- **Rendered view** — the document as formatted prose. Click any heading,
  paragraph, bullet, table, diagram or code block to comment on it.
- **Source view** (`/d/<slug>/v/<n>/raw`) — numbered lines. Click one, shift-click
  another to extend. This is how you comment on a single line *inside* a fenced
  code block, which block anchoring cannot isolate.
- **Changes view** (`/d/<slug>/diff/<a>/<b>`) — a unified line diff between two
  versions, so you can see what a revision actually changed.
- **Theme** — light, dark, or follow the system, remembered across visits.

Markdown task lists render as real checkboxes. They are read-only: the agent owns
the file, so nothing on the page can edit a document that is about to be revised.

Fenced blocks tagged `mermaid` render as diagrams. A diagram that fails to parse
shows its source instead, so a malformed one never hides content. Mermaid is
vendored and loaded only on pages that actually contain a diagram.

## How it works

- **A review round is a version.** Every `submit` snapshots the content and its
  SHA-256. Versions are immutable, and review status lives on the version row.
- **Comment anchors cannot drift.** A comment points at a line range inside a
  frozen version, so it can never end up attached to the wrong text. When you
  submit a revision, prior comments are marked `outdated` rather than relocated.
- **Block anchoring** uses `markdown-it-py`'s `token.map`, which reports the
  source line range behind each block token. That yields separate anchors for
  headings, paragraphs, individual list items and code blocks.
- **Idempotent submission.** Resubmitting identical content while a review is
  pending reuses the round, so an agent retrying `submit` cannot discard comments
  you are midway through writing.
- **No daemon.** The CLI starts a server when it needs one.

## Configuration

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `MDREVIEW_PORT` | `7391` | Port to bind and connect to |
| `MDREVIEW_HOST` | `127.0.0.1` | Loopback, or one private IP with LAN opt-in |
| `MDREVIEW_DATA_DIR` | `~/.local/share/mdreview` | Database and logs |
| `MDREVIEW_AUTOSTART` | `1` | Set `0` to fail instead of starting a server |
| `MDREVIEW_ALLOW_LAN` | `0` | Set `1` to permit a private-LAN bind |
| `MDREVIEW_WEBHOOK_URL` | unset | POST every decision here as it is recorded |
| `MDREVIEW_WEBHOOK_TOKEN` | unset | Bearer token presented to that endpoint |

The server refuses to bind outside loopback by default: it has no authentication,
so listening on a routable interface would expose every document to the network.

To review from a phone on the same private network, bind one specific interface
explicitly:

```bash
mdreview serve --host 10.31.41.35 --allow-lan
```

Wildcard (`0.0.0.0` / `::`) and public addresses remain forbidden even with the
opt-in.

### The LAN token

A server bound to a LAN address requires a **capability token** from anything
that is not loopback. The URL printed at startup contains it, so opening that
link on your phone is all that is needed — the token is then remembered in a
cookie for that origin.

Requests from loopback never need the token, so the agent CLI is unaffected.

```
warning: reviews are exposed on the network. Open this link to authorise a
device; anyone holding it can read and change reviews:
http://10.31.41.35:7391/?t=<token>
```

The token lives at `~/.local/share/mdreview/lan_token`, mode `0600`. Delete that
file to revoke every device; the next LAN start mints a new one.

### Running it always, for a tablet

```bash
mise run install-service     # start it now and on every login
mise run service-status      # running on 10.31.41.9 (pid 1532)
mise run uninstall-service   # stop it and remove it completely
```

The service resolves your private address at **every start**, so a changed DHCP
lease is handled by restarting it rather than reinstalling. `mdreview lan-address`
prints what it would pick, and `mdreview serve --host auto --allow-lan` does the
same thing interactively.

Bookmark your machine's Bonjour name on the tablet rather than an IP —
`http://<your-hostname>.local:7391/?t=<token>` — because the name survives DHCP
changes and a literal address does not.

Two things worth knowing:

- Once installed, the server is running whenever you are logged in. Rotating the
  token is how you revoke a device, not stopping the server.
- On the machine itself, that `.local` name may resolve to `127.0.0.1` and reach
  the loopback server, which needs no token. From another device it resolves to the
  private address and the token is required. Do not read a token-less `200` on your
  own machine as the guard being off.

A server binds one address, so a LAN-bound server is not listening on loopback.
The agent will simply start its own loopback server on demand, and the two share
the same SQLite database in WAL mode — a document submitted by the agent appears
immediately on the LAN server. Nothing needs configuring for this; it is just
worth knowing that two processes is the normal shape when LAN access is on.

**What this does and does not protect.** The token stops other machines on a
shared network from casually reaching your reviews. Traffic is plaintext HTTP by
design, so it is **not** protection against someone able to read packets on the
wire, and anyone with a shell on your machine can read the token file just as
they can read the database. Stop the server when you are done.

On macOS, the application firewall may prompt before allowing the Python
interpreter to accept incoming connections. Approve that prompt for direct LAN
mode; do not disable the firewall globally.

### Decision webhook

`mdreview await` tells the agent that submitted a document how its own review
went. To let something else react to *every* decision — a chat notifier, a CI
job that starts on approval, a dashboard — point `MDREVIEW_WEBHOOK_URL` at an
endpoint and each recorded decision is POSTed to it as JSON:

```json
{
  "slug": "plan",
  "version": 2,
  "status": "approved",
  "note": "ship it",
  "decided_at": "2026-08-15T09:12:44+00:00"
}
```

Both the review page and the API fire it, and a version can only be decided
once, so each version produces at most one call.

If the receiver authenticates its callers, set `MDREVIEW_WEBHOOK_TOKEN` and the
POST carries it as a bearer credential:

```
Authorization: Bearer <token>
```

Leave it unset and no `Authorization` header is sent. Note that the token is
only as protected as the URL it is sent to: over `http://` on an untrusted
network it travels in the clear, like everything else this tool sends.

Delivery is fire-and-forget: it happens on a background thread and every
failure is ignored, because a listener being down must never fail a decision
you have already made. There are no retries — a missed event is missed, and
`GET /api/documents/{slug}/state` remains the authoritative answer for a
consumer that wants to reconcile on startup. Unset — the default — sends
nothing.

## Development

```bash
mise run test      # pytest
mise run lint      # ruff check
mise run fmt       # ruff format
mise run check     # all three
mise run serve     # foreground server
```

The specification lives in `openspec/`. `openspec show add-markdown-review-loop`
renders the proposal, capability specs, design and task breakdown.

## Licence

MIT
