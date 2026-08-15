## 1. Announcing a decision

- [x] 1.1 `MDREVIEW_WEBHOOK_URL`, its loader, and the `Settings` field carrying
  the resolved value
- [x] 1.2 `notify.py`: `fire_decision` posting the decision on a daemon thread,
  swallowing every failure, and doing nothing when no endpoint is configured
- [x] 1.3 Fire from the review page's decision handler, after `store.decide`
  has committed
- [x] 1.4 Fire from the API's decision endpoint, after `store.decide` has
  committed
- [x] 1.5 `MDREVIEW_WEBHOOK_TOKEN`, its loader and `Settings` field, sent as
  `Authorization: Bearer <token>` when set and omitted entirely when not
- [x] 1.6 README: both variables, the payload, the header, and the
  at-most-once contract

## 2. Verification

- [x] 2.1 A decision with an endpoint configured sends exactly one request
  carrying the slug and version, with the bearer header present when a token
  is configured and absent when it is not
- [x] 2.2 Full suite, ruff check and format
