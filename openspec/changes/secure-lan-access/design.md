## Context

LAN access shipped unauthenticated, with the exposure recorded as an accepted risk. In
practice the LAN is a shared office network, which makes "anyone who can route here" a
real population rather than a theoretical one. The gap is worth closing, and closing it
is cheap.

The hard constraint is asymmetry: the reviewer touches the server a handful of times
from a phone, while the agent touches it constantly from loopback. Any scheme that adds
a credential to the agent's path would be paid on every command for no gain.

## Goals / Non-Goals

**Goals:**

- Stop another machine on the network from reading or mutating reviews.
- Cost the reviewer one tap, with nothing to type.
- Cost the agent nothing at all.
- Keep the failure mode obvious rather than a silent partial denial.

**Non-Goals:**

- TLS, accounts, roles, expiry, or session management.
- Defending against someone who can read packets on the wire, or who already has a shell
  on the machine.
- Authenticating loopback.
- Everything in the proposal's Non-goals section.

## Decisions

### D1. Authorise on the client address, not on a route list

A single check runs per request: if the peer address is loopback, serve it; otherwise
require the token. Keying on the peer rather than enumerating protected routes means a
route added later is protected by default. The failure mode of the alternative — forget
to list a new route — is silent and total.

This is what keeps the agent free: it always connects over loopback, so it never sees a
credential, and `mdreview` needs no new flags.

### D2. A capability URL, then a cookie

The token is a bearer capability carried in the query string of the URL the server
prints. On a request that presents a valid token, the server sets it as a cookie scoped
to that origin, and subsequent requests are authorised by the cookie. This is the model
Jupyter uses, for the same reason: it is the only scheme where the reviewer's entire
interaction is "open the link".

The cookie is `HttpOnly` and `SameSite=Lax`. `Secure` is deliberately not set, because
the service is plaintext HTTP by design and the flag would prevent the cookie being
stored at all.

*Alternative considered:* HTTP Basic auth. Rejected — it requires typing a password on a
phone, and browsers cache it in ways that are awkward to clear.

*Accepted weakness:* a token in a URL can leak through history or a shared screenshot.
Rotation is the mitigation, and the exposure window is a private network.

### D3. Comparison is constant-time, and failure leaks nothing

Tokens are compared with `secrets.compare_digest`. A rejected request returns 403 with a
fixed body: no document titles, no slugs, no indication whether a document exists.
Distinguishing "wrong token" from "no such document" would hand an unauthenticated
caller a way to enumerate the store.

### D4. Storage in the data directory, owner-only

`~/.local/share/mdreview/lan_token` alongside the database, created with mode `0600`.
The token has 256 bits from `secrets.token_urlsafe`, comfortably above the 128-bit
requirement.

It is generated lazily on first LAN use, not on install, so a loopback-only user never
has a credential on disk. It persists across restarts because a token that changed on
every start would invalidate the phone's cookie constantly.

Rotation is deleting the file, or an explicit command; both cause the next LAN start to
mint a new one.

*Alternative considered:* storing it in SQLite. Rejected — the database is review data,
and a file is easier to inspect, delete, and permission.

### D5. Loopback detection must not be spoofable by a header

The peer address comes from the connection, never from `X-Forwarded-For` or any other
request header. There is no proxy in front of this service, so any such header is
attacker-controlled input; honouring it would let a LAN client claim to be loopback and
bypass the check entirely. This is the one place where getting it wrong silently defeats
the whole feature.

## Risks / Trade-offs

- **A token in a URL can leak via history or a screenshot.** → Rotation, and the URL only
  ever travels over a private network. Considered acceptable for the same reasons
  Jupyter does.
- **Plaintext HTTP means the token is visible to anyone reading packets.** → Explicitly
  out of scope; the token defends against casual access by other machines, not against a
  network-level observer. Stated plainly in the docs rather than implied.
- **A stale cookie after rotation looks like a broken page.** → The refusal is an
  explicit 403 with an instruction to reopen the printed link, not a blank page.
- **Someone with a shell on the machine can read the token.** → So can they read the
  database; this is not a boundary the tool claims to defend.
- **A future route forgets to authorise.** → Prevented structurally by D1: the check is
  per request, not per route.

## Migration Plan

No data migration. The token is created on first LAN start. Existing LAN URLs without a
token stop working and must be reopened from the newly printed link — the only breaking
change, confined to LAN use. Loopback behaviour is untouched.

Rollback is reverting the middleware; the token file becomes inert and can be deleted.

## Open Questions

None blocking. If the URL-borne token proves awkward in practice, a short-lived pairing
code exchanged for the cookie would remove the token from the URL entirely, at the cost
of a second step for the reviewer.
