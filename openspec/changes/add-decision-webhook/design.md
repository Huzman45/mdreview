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

`fire_decision` suppresses `Exception` around both the delivery and the thread
spawn, and returns nothing. This is deliberately broader than the
`except httpx.HTTPError` that would cover the expected failures: the value
being protected is that a review tool never fails a recorded decision because
of a listener, and that value should not depend on having enumerated the
failure modes correctly. The decision is already committed by the time the call
is reached (D3), so there is nothing to roll back and nothing a caught error
could usefully change.

Guarding the *spawn* matters as much as guarding the POST. An exception raised
on the delivery thread cannot reach the handler at all, so the only way an
announcement could still fail a decision is `Thread.start()` raising in the
handler itself — under thread exhaustion — after the row is committed. That
narrow case is what the outer suppression closes.

`BaseException` was considered and rejected: around a daemon thread's bootstrap
it would swallow `SystemExit` and `KeyboardInterrupt` during interpreter
shutdown, and every failure worth surviving here is an ordinary exception.

The cost is that a misconfigured URL is silent, and — since D8 — so is a
rejected token: a 401 is just another response the sender never reads. Accepted
in the reviewer's sidebar, which is the point. It is also silent in the server
log, which is a consequence of this codebase having no logging rather than a
decision about webhooks; recorded here so the next reader takes it as chosen
rather than overlooked.

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

One qualification, since this change states the guarantee to users: it is
advisory rather than absolute. `decide` tests `version.status.is_decided` in
Python and then issues an unguarded `UPDATE`, so two genuinely concurrent
decisions on one pending version could both pass the check and both announce.
Decisions are human-paced and this has never been reachable in practice, but
the two-server shape the README already describes — a loopback server and the
LAN service over one database — makes it less hypothetical than single-process
reasoning suggests. Making it absolute costs a `WHERE id = ? AND status =
'pending'` and a `rowcount == 0 → Conflict`; that belongs to `review-decisions`
proper rather than to the hook, and this change deliberately does not touch the
SQL layer.

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
settings rather than the environment. `MDREVIEW_WEBHOOK_TOKEN` (D8) follows the
identical shape, which is also why it is an environment variable rather than a
flag: a secret does not belong in a command line, where it lands in shell
history and in every `ps` listing on the machine.

### D8. Optional bearer, and nothing more

A receiver worth notifying often does something privileged with the news, and
anything privileged has to authenticate its callers. A URL is the only thing
this feature otherwise carries, and a URL cannot express an `Authorization`
header — so without a token the hook can target only completely
unauthenticated endpoints. That is a strange limitation for a tool whose own
design refuses public binds *because* it has no authentication.

`MDREVIEW_WEBHOOK_TOKEN` therefore adds exactly one header,
`Authorization: Bearer <token>`, and only when it is set. Bearer was chosen
over the alternatives because it assumes least: it is the scheme
(RFC 6750) that receivers behind an API gateway, a reverse proxy, or a
framework's auth middleware already accept without configuration. A
query-string token would leak into the receiver's access logs and into any
redirect; a custom header name would require the operator to configure both
ends to agree on a spelling; basic auth would imply a username that does not
exist here.

The token is a value carried from the environment into one outbound header. It
is never logged, never rendered into a page, and never returned by any
endpoint. Because the sender never reads the response (D2), a receiver that
rejects the token is indistinguishable here from one that is switched off — the
right outcome, since neither is the deciding reviewer's problem, but worth
stating because it means a wrong token fails silently.

Note that the token authenticates mdreview *to* the receiver. It does not prove
to the receiver that a given request came from mdreview and was not tampered
with; that is signing, which the proposal keeps out of scope.

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
  compatible for any consumer reading by key. Nothing in it is shaped for a
  particular consumer — no event type, no routing discriminator — because a
  field that exists for one listener's dispatch logic is a field every other
  listener has to ignore forever.
- **A token sent over plain HTTP is exposed to anyone on the path.** The
  operator chooses the URL; an `https://` receiver protects the token, an
  `http://` one on an untrusted network does not. Consistent with the rest of
  the tool, which is plaintext by design and says so, but it is the operator's
  call to make knowingly — hence the README saying it outright.
- **A wrong token is silent** (D2, D8). The failure mode of a misconfigured
  receiver is "nothing arrives", which looks identical to a misconfigured URL.
