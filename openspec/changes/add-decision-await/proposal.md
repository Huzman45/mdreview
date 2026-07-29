## Why

The loop today: the agent submits, stops, and the human — after deciding in
the browser — must remember to type "done" in the right chat before the agent
runs `mdreview review`. That last step is the friction: the decision exists,
recorded and final, and the only thing between it and the agent is a human
courier. With several agents in flight, "the right chat" is itself a lookup.

This change is the requested investigation into how the tool could notify
agents, with the option that survived it implemented.

## The investigation

The original design (2026-07-25, decision 4 and D7) rejected *"any blocking
or push mechanism — no long-poll, no websockets, no notifications"*, for two
reasons: an agent must not hold its turn open across a human-scale delay, and
nothing should require a daemon. Both reasons still stand — but two premises
under them have changed since:

1. **A persistent server now exists as an opt-in** (the LAN service, PR #21),
   so "would require a daemon" is no longer automatically disqualifying.
2. **Agent harnesses can now run background tasks and wake the agent when
   one completes.** Claude Code's shell tool does exactly this. That
   mechanism did not exist when decision 4 was made; it changes what
   "waiting" costs, because a background process can wait while the agent's
   turn still ends.

Options considered:

- **A. Agent-side poll loop in the foreground** (the exit-3 loop designed
  and dropped originally). Re-rejected: it holds the agent's turn open,
  burning the context window against a human-scale delay — exactly what
  decision 4 exists to prevent.
- **B. `mdreview await <slug>` run as a background task** — a client-side
  poll of the existing state endpoint, exiting with the review exit code the
  moment a decision lands. The agent's turn still ends; the harness delivers
  the completed task back to it. No server change, no held connections, no
  daemon requirement (the poll rides the existing autostart), and the exit
  contract is the one agents already know. **Chosen — see design.**
- **C. Server-side notify hook** (a command the server runs on decision,
  handed slug, status, and — since session provenance landed — the
  originating tool and session id). Powerful, and the natural place for a
  macOS notification or a future "resume the session" integration. Deferred:
  what to *run* is unclear today — neither tool supports injecting input
  into a live interactive session, so the hook could only notify the human,
  who is already in the browser deciding. Worth revisiting when a concrete
  consumer exists; nothing in B blocks adding it.
- **D. A file the harness watches.** Writing a marker file on decision
  assumes a watcher; no agent harness here watches files natively, so this
  reduces to B with extra moving parts.
- **E. Web push / websockets to the page.** Notifies the human, who already
  knows — they made the decision. Solves nothing in this loop.

## What Changes

- **`mdreview await <slug>`**: poll the document's state until its latest
  version is decided, then print the same report as `review` and exit with
  the same code. `--timeout` bounds the wait (default eight hours), exiting
  3 — still undecided — which is already the code agents treat as "do not
  proceed". Brief server restarts are ridden out; a server that never comes
  back is exit 5, distinct from any verdict, as ever.
- **The skill teaches the hands-free variant**: after submitting, start
  `mdreview await` as a background task where the harness supports one, and
  end the turn as before. When the task completes, branch on its exit code
  exactly as for `review`. The foreground rule — never block your turn on a
  review — is restated, not relaxed.

## Capabilities

### Modified Capabilities

- `agent-cli`: gains the awaiting requirement.
- `agent-skill`: gains the background-await guidance.

## Non-goals

- **Foreground blocking.** `await` exists to be backgrounded; the skill
  forbids holding a turn open on it, same as always.
- **Server push.** No websockets, no SSE, no held HTTP connections; the
  server remains request-response.
- **The notify hook (option C).** Deferred until something concrete can
  consume it; this change neither builds nor precludes it.
- **Notifying the human.** The browser already does that.

## Impact

- `cli.py` (one command), `report.py` untouched, skill, README, specs.
  No server, schema, or API change.
