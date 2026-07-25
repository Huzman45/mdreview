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

Put the CLI on your `PATH`:

```bash
uv tool install --editable .
```

Then install the agent skill so your agent reaches for it unprompted:

```bash
mkdir -p ~/.agents/skills
cp -r skill/md-review ~/.agents/skills/
ln -s ../../.agents/skills/md-review ~/.claude/skills/md-review   # if you use ~/.claude/skills
```

## Use

```bash
mdreview submit PLAN.md          # publish, open the browser, print the URL
mdreview review plan             # read the outcome; the exit code is the answer
mdreview resolve plan C1 C2      # mark comments addressed
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
| 2 | `changes_requested` | Address comments, resolve, resubmit |
| 3 | `pending` — no decision recorded | Report and wait; **do not** proceed |
| 4 | `cancelled` | Stop and ask |
| 5 | API unreachable | Infrastructure failure, not a verdict |

Code 3 is the important one. In a hands-off loop you will sometimes nudge the
agent before you have actually clicked anything, and an agent that reads "no
changes requested" as "approved" would implement an unreviewed plan.

### Output shape

`review` renders feedback for a language model to act on without re-reading the
file:

```
STATUS: changes_requested   VERSION: 1   UNRESOLVED: 2

--- unresolved comments (2) ---

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

The server refuses to bind outside loopback by default: it has no authentication,
so listening on a routable interface would expose every document to the network.

To review from a phone on the same private network, bind one specific interface
explicitly:

```bash
mdreview serve --host 10.31.41.35 --allow-lan
```

Wildcard (`0.0.0.0` / `::`) and public addresses remain forbidden even with the
opt-in. Anyone able to reach the chosen private address can read documents, add
comments, and record decisions, so stop the server when you are done.

On macOS, the application firewall may prompt before allowing the Python
interpreter to accept incoming connections. Approve that prompt for direct LAN
mode; do not disable the firewall globally.

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
