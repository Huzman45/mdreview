## Why

The Decided section is one undifferentiated run of rows. With a few days of
work in it, "what did I decide yesterday?" means reading every relative
timestamp; there is no temporal structure to scan by.

## What Changes

- **Decided documents group by day**, most recent day first: Today,
  Yesterday, then explicit dates. Rows inside a day stay newest-first.
- **"Waiting for you" stays a flat queue.** The status split is the index's
  deliberate design — the page answers "what needs my attention", and the
  attention queue is short by nature; date headers over two rows would be
  noise. Date grouping nests inside the existing structure rather than
  replacing it.
- Days follow the reviewer's clock, not UTC: a review decided at 00:30 local
  time belongs to "Today", whatever Greenwich thinks.

## Capabilities

### Modified Capabilities

- `review-decisions`: the index's decided listing gains day grouping.

## Non-goals

- **Replacing the status split.** That was the point of the index rebuild
  (PR #23); this change deliberately keeps it and adds time structure inside
  it. If a flat all-dates index is what was actually wanted, that is a
  reversal to make explicitly, not en passant.
- **Grouping by session.** The original request said "sessions" where the
  index lists documents; once documents can be traced to sessions (a later
  change in this batch), grouping by session becomes possible — as its own
  decision.
- **Grouping the archived listing**, which is already ordered by when things
  were shelved and is visited rarely.

## Impact

- `web.py` (grouping helpers, index context), the index template, a day
  subhead style. No storage, API, or CLI change.
