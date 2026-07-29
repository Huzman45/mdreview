## Context

Decision 4 of the original design fixed the handshake: submit, stop, be
nudged, read the outcome. The nudge is the loop's one manual step. The
proposal for this change records the investigation; this document records how
the chosen option is built and why its details are safe against the original
rejections.

## Goals / Non-Goals

**Goals:** the agent learns the outcome without the human typing "done",
without the agent's turn outliving the submit, and without new server
machinery.

**Non-Goals:** push; hooks; anything the server must remember between
requests.

## Decisions

### D1. Awaiting is a client concern

`await` is a poll loop around the existing state endpoint — the server does
not know it is being awaited. This keeps every original property: the server
holds no connections, restarts remain invisible (state is in SQLite), and
the autostart path is exercised rather than bypassed. A two-second interval
against loopback costs nothing measurable; the alternative of long-polling
would put a held connection back into a server designed not to have any.

### D2. The exit contract is `review`'s, verbatim

`await` terminating is the notification, and its exit code is the message:
0 approved, 2 changes requested, 4 cancelled — and on timeout, 3, which
agents already read as "no decision; do not proceed". A new vocabulary here
would force every consumer to learn two mappings for one concept. The final
report body is `review`'s too, so the completed task carries the comments
with it and the agent need not run anything else.

### D3. Timeout by default, because background tasks outlive interest

A background `await` whose session was abandoned should not idle forever.
The default timeout is eight hours — long enough for review-when-I-wake-up,
short enough that orphans clear themselves — and `--timeout` overrides it.
Timeout exits 3 without prejudice: the round is still open, and a fresh
`await` resumes watching it.

### D4. Transient unreachability is ridden out; persistent is exit 5

The loop tolerates the server vanishing between polls (an upgrade restart,
an autostart race): each poll re-runs the client's ensure-up path, and only
sixty consecutive unreachable seconds — capped by the timeout — end the wait
with exit 5. Exit 5 is reserved for "never got an answer", so a wait that
never reached the server at all reports 5 rather than 3: "undecided" is a
statement about the review, and an unreachable server cannot make it.

### D5. The watch is on the document, not a version number

`await` exits when the document's *latest* version is decided, whichever
version that is by then. Pinning to the version present at start would miss
the human deciding a just-resubmitted revision, and the agent acting on the
outcome always acts on the latest state anyway — `review`'s own semantics.

### D6. The skill backgrounds it and keeps the foreground rule

The skill's instruction stays "submit, tell the user, end your turn" — with
"start `mdreview await` as a background task first" where the harness offers
one. The harness delivering the finished task is what replaces the human's
nudge; in harnesses without background tasks, nothing changes at all.

## Risks / Trade-offs

- **Orphaned awaits when a session dies.** Bounded by the default timeout;
  each orphan is one sleeping process polling loopback until it expires.
- **A decided-then-instantly-superseded round** between two polls makes
  `await` keep waiting on the new pending version. Consistent with D5, and
  the resubmission was the agent's own act.
- **Two agents awaiting one document** both wake on the decision. Harmless:
  the exit code is a fact about the document.
