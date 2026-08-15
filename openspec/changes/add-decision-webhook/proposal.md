## Why

`add-decision-await` (2026-07-29) surveyed five ways to tell an agent that a
decision landed, shipped option B — `mdreview await`, a client-side poll — and
deferred option C, the server-side notify hook, on one explicit ground:

> *what to run is unclear today — neither tool supports injecting input into a
> live interactive session, so the hook could only notify the human, who is
> already in the browser deciding. Worth revisiting when a concrete consumer
> exists; nothing in B blocks adding it.*

Concrete consumers now exist, and they are not agent harnesses. They are the
ordinary things that sit next to a review loop: a chat notifier, a CI job that
should start on approval, a dashboard, a script that files the approved plan.
Each of those has to poll `/api/documents` today, on a timer, forever, to learn
about an event that the server knew about the instant it happened.

`await` remains the right answer for the agent that submitted the document —
one document, one waiter, exits with the verdict. It is the wrong shape for
anything watching *all* reviews: a watcher of ten documents runs ten polls to
observe an event that happens a handful of times a day.

## What Changes

- **`MDREVIEW_WEBHOOK_URL` names one HTTP endpoint.** Unset — the default —
  nothing is sent and nothing changes.
- **Recording a decision POSTs a small JSON body to it**: the slug, the version
  number, the status, the decision note, and the decision timestamp. Enough to
  act on without a follow-up read; nothing that presumes what the consumer is.
- **`MDREVIEW_WEBHOOK_TOKEN` presents a bearer token when the receiver wants
  one.** Set, the POST carries `Authorization: Bearer <token>`; unset, it
  carries no such header and nothing changes. A receiver that does anything
  privileged on a decision has its own reason to authenticate its callers, and
  a URL cannot carry an `Authorization` header — so without this the hook can
  only ever target a completely unauthenticated endpoint. For a tool that
  refuses public binds precisely because it has no authentication of its own,
  being unable to talk to anything that does is an awkward gap.
- **Delivery never touches the review.** The POST goes out on a daemon thread
  and every failure — refused connection, timeout, 500, rejected token,
  malformed URL — is swallowed. A reviewer clicking Approve must not see an
  error, or a delay, because a listener somewhere is down or does not like the
  token.
- **Both decision surfaces fire it**: the browser button and the REST endpoint.
  `store.decide` is the single chokepoint they share and it admits exactly one
  decision per version, so a decided version emits exactly one event.

## Capabilities

### Modified Capabilities

- `review-decisions`: a recorded decision is announced to an optionally
  configured endpoint.

## Non-goals

- **Retries, queues, or delivery receipts.** A dropped event is dropped. The
  state endpoint remains authoritative and is one GET away, so at-most-once
  delivery costs a consumer a reconciliation on startup rather than
  correctness. Durable delivery means a spool, a retry schedule, and a backlog
  to garbage-collect — a message broker grown inside a single-user local tool.
- **Several endpoints.** One URL covers the cases above; a consumer that needs
  fan-out is a consumer that should own a fan-out.
- **Signing the callback.** Presenting a bearer token proves to the receiver
  that the caller is authorised; an HMAC signature over the body would prove
  the message came from *this* server and was not altered. That is the opposite
  direction and a larger commitment — a shared secret, a canonical body
  encoding, a documented verification recipe — and the server it would speak
  for is itself unauthenticated by design and loopback by default. Nothing here
  precludes it.
- **Any scheme other than bearer.** No basic auth, no per-receiver custom
  header names, no OAuth refresh. One token in one standard header is the
  least-opinionated thing that works with an authenticated receiver; anything
  more starts encoding assumptions about who is listening.
- **Announcing the cancellation that `archive` records.** See design D5: it is
  a `document-lifecycle` act, and reaching it cleanly is a separate change.
- **Blocking the decision on delivery.** The reason the thread is a daemon.

## Impact

- `config.py` (two environment variables, their loaders, two `Settings`
  fields), a new `notify.py`, one call each in `web.py` and `api.py`, README.
  No schema change, no API surface change, no new dependency — `httpx` is
  already used by the CLI client.
- The token is read from the environment and held in `Settings` beside the URL.
  It is never logged, never rendered, and never returned by any endpoint; the
  only thing that happens to it is being put in an outbound header.
