## Context

Decision 4 of the original design — no blocking, human hands off — and D1 of
`add-decision-await` — awaiting is a client concern — between them made the
server request-response and kept it that way. This change adds the first
outbound call the server has ever made, so the burden here is showing that it
takes nothing back from those two decisions.

It does not. Nothing is held: the POST is fired and forgotten, so the server
still holds no connections and still remembers nothing between requests. A
restart mid-review is still invisible, because there is no queue to lose.
`await` is untouched and stays the agent's path.

## Goals / Non-Goals

**Goals:** a consumer outside the review loop learns of a decision without
polling; the decision itself is never slowed, failed, or altered by that
consumer; the whole thing is inert when unconfigured.

**Non-Goals:** durable delivery, retries, fan-out, callback authentication,
inbound push to the page, and any change to how a decision is recorded.

## Decisions

### D1. An outbound POST, not a spawned command

Option C in `add-decision-await` was framed as *a command the server runs*.
An HTTP callback is the better shape for the same idea. A command inherits the
server's environment and privileges and turns a configuration string into
arbitrary local execution; a URL is inert until something chooses to listen at
the other end. It also crosses the machine boundary, which the interesting
consumers — a chat notifier, a CI trigger — are already on the far side of.
A consumer that genuinely wants to run something locally writes three lines of
listener and keeps that decision in its own process, not in this one.

### D2. Failure is invisible, by construction

`fire_decision` catches `BaseException` around the whole delivery and returns
nothing. This is deliberately broader than the `except httpx.HTTPError` that
would cover the expected failures: the value being protected is that a review
tool never fails a recorded decision because of a listener, and that value
should not depend on having enumerated the failure modes correctly. The
decision is already committed by the time the call is reached (D3), so there
is nothing to roll back and nothing a caught error could usefully change.

The cost is that a misconfigured URL is silent. Accepted: the alternative is
surfacing an infrastructure error in the reviewer's sidebar, next to a
decision that was in fact recorded.

### D3. Fired after the commit, from the request layer

`db.connect` uses `isolation_level=None`, and neither decision path wraps
`store.decide` in `transaction()`, so the row is committed the moment
`store.decide` returns. Both call sites therefore fire *after* it, and a
consumer that reacts by immediately reading `/api/documents/{slug}/state` is
guaranteed to see the decision it was told about — the failure that makes
webhooks over transactions notorious.

The hook does not live inside `store.decide`. `store.py` is the SQL layer;
giving it a network dependency would mean every future caller — a migration, a
test helper, a batch fixup — silently emits events, and `archive_document`
already calls `decide` from *inside* a `transaction()` block, which is exactly
the pre-commit fire this decision exists to avoid. The two request handlers are
the only places a *reviewer* records a decision, which is the event being
described.

### D4. One event per version comes free

`store.decide` raises `Conflict` on a version that is already decided, so a
version transitions out of `pending` exactly once in its life. The event
inherits that: at most one POST per version, with no idempotency key,
deduplication window, or delivered-flag column. The constraint that already
protects the agent from acting on a reversed decision protects the consumer
from acting on a duplicate one.

### D5. The archive cancellation is left out of this change

`archive_document` records `cancelled` through `decide`, with the note
"archived without review" — the store's own account of why it is not a review
decision. Announcing it is defensible and probably wanted eventually, but not
reachable cleanly from here: firing inside `archive_document` would fire before
its `transaction()` commits, violating D3, and firing from the web handler
means restating the store's cancel-only-if-pending condition where it would
drift out of step with the store's copy.

It is additive when it comes: same payload, one more status value, and it
belongs to `document-lifecycle` rather than to this capability. Consumers that
must not hang on a shelved document have the same recourse `await` gives
itself — a timeout — until then.

### D6. `httpx`, with the environment trusted

`httpx` is already a dependency and already how this codebase makes HTTP
requests. Unlike the CLI client, this one leaves `trust_env` at its default:
that client sets `trust_env=False` because its only legitimate targets are
loopback or one private IP, whereas a webhook URL points wherever the operator
put their listener, which may legitimately be through a proxy.

The timeout is five seconds. Nothing waits on it, so its only job is to stop an
unresponsive listener from pinning a thread indefinitely.

### D7. Configured by environment alone

No CLI flag. Every existing flag — `--allow-lan`, `--host` — configures
something the person typing the command is about to look at; a webhook is
configured once for the machine and then forgotten, which is what an
environment variable is for. It follows `config.py`'s established shape all
the same: a module constant for the name, a loader that reads it, and a
`Settings` field that carries the resolved value, so the request handlers read
settings rather than the environment.

## Risks / Trade-offs

- **A slow listener leaks threads.** One thread per decision, bounded by the
  five-second timeout and by decisions being a human-paced event. A thread pool
  would bound it harder at the cost of machinery this event rate cannot
  justify.
- **Delivery is at-most-once.** Stated as a non-goal, mitigated by the state
  endpoint remaining authoritative: a consumer that missed an event finds it on
  its next reconciliation.
- **Interpreter shutdown can cut a delivery short**, since the thread is a
  daemon. Correct precedence — a pending notification must not delay `mdreview
  stop`.
- **The payload is a contract now.** Kept to facts about the decision, which
  are the fields least likely to need to change; additions stay backward
  compatible for any consumer reading by key.
