## Why

Private-LAN access shipped deliberately unauthenticated, with the risk recorded as a
trade-off and a bearer token noted as out of scope. That trade-off is worse than it
first appears: the networks this is actually used on are shared office networks, so
"anyone who can route to this address" is not a hypothetical adversary but every other
machine on the LAN. Anyone reaching the port can read every plan under review, add
comments in the reviewer's name, and approve or reject work on their behalf.

The protection needs to cost the reviewer nothing, and must not add friction to the
agent, which talks to the same server over loopback many times per review.

## What Changes

- Enabling LAN access generates a **capability token**. Requests arriving from a
  non-loopback address must present it; requests from loopback continue to need nothing,
  so the agent CLI is unaffected.
- The token is embedded in the URL printed when the server starts, so opening the link
  on a phone authenticates in one step and nothing has to be typed.
- Once presented, the token is remembered by the browser for that origin, so navigating
  between pages and posting comments continue to work without the token in every URL.
- An unauthenticated LAN request is refused with a response that does not leak document
  content or existence.
- The token is stored in the data directory with owner-only permissions and can be
  rotated by regenerating it.
- **BREAKING** for LAN use only: existing bookmarked LAN URLs without a token will be
  refused. Loopback URLs are unaffected.

## Capabilities

### Modified Capabilities

- `private-lan-access`: LAN exposure additionally requires a capability token; the
  opt-in alone is no longer sufficient to serve requests from another machine.

## Non-goals

- **User accounts, passwords, or roles.** A single reviewer holds a single token.
- **TLS.** Traffic stays plaintext on a private network. A token stops casual access; it
  is not protection against someone able to read packets on the wire.
- **Authenticating loopback.** The agent runs many commands per review and gains nothing
  from a credential shared with the process that issued it.
- **Public internet exposure.** Still refused; the address allow-list is unchanged.
- **Token expiry or session management.** The token lives until it is rotated.
- **Protecting against a hostile local user.** Anyone with a shell on the machine can
  read the token file, exactly as they can read the database.

## Impact

- A request-time check on the server, keyed on whether the client address is loopback.
- Token generation, storage in the data directory with restrictive permissions, and
  rotation.
- The URL the CLI prints for LAN mode gains a token parameter; loopback output is
  unchanged.
- Anyone currently using a LAN URL must reopen the tokenised link.
- No change to the database schema, the comment model, or the agent-facing exit codes.
