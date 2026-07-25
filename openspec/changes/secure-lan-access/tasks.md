## 1. LAN capability token

- [ ] 1.1 Add token generation using `secrets.token_urlsafe`, stored at
  `lan_token` in the data directory with mode `0600`, created lazily on first LAN use
- [ ] 1.2 Add a rotation entry point that discards the current token so the next LAN
  start mints a new one
- [ ] 1.3 Add request authorisation keyed on the peer address: loopback is served
  unconditionally, everything else must present the current token
- [ ] 1.4 Take the peer address from the connection only, never from a request header, so
  a LAN client cannot claim to be loopback
- [ ] 1.5 Accept the token from a query parameter or a cookie, comparing with
  `secrets.compare_digest`
- [ ] 1.6 Set the token as an `HttpOnly`, `SameSite=Lax` cookie when a valid query
  parameter is presented, so later requests need no token in the URL
- [ ] 1.7 Refuse unauthorised requests with 403 and a fixed body that reveals no
  document titles, slugs, content, or existence
- [ ] 1.8 Include the token in the URL printed when serving on a private address, and
  keep loopback output unchanged
- [ ] 1.9 Tests: loopback needs no token; a valid token is served and sets a cookie; the
  cookie authorises later requests; missing, wrong and rotated tokens are refused;
  comment and decision endpoints are protected; a forged forwarding header does not
  grant loopback treatment; the refusal body leaks nothing; the token file is `0600` and
  stable across restarts
- [ ] 1.10 Document the token, rotation, and the explicit absence of TLS in the README,
  including that the token does not protect against a network-level observer
- [ ] 1.11 Verify by hand: the tokenised URL loads on a phone, a token-less URL from the
  same device is refused, and the agent CLI over loopback is unaffected
