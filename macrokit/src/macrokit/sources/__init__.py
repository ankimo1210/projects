"""Per-source adapters.

There are two adapter shapes, depending on whether the source is addressable
per series:

  Indicator-scoped (ALFRED): the source can be queried one series at a time.
    probe(indicator)     -- cheapest possible check for "has anything changed"
    fetch_raw(indicator) -- the bytes, exactly as the source served them
    parse(indicator)     -- those bytes as Observation rows

  Whole-source (MoF JGB): the source publishes one payload covering
  everything it has, with no per-indicator addressing -- there is nothing to
  probe *for*, so these adapters have no `probe` at all.
    fetch_raw()           -- the bytes, exactly as the source served them
    parse(payloads)       -- those bytes as rows

Both shapes are deliberately separable into fetch and parse. An adapter with
`fetch_raw` but no working `parse` still reaches the `fetching` state, which
is enough to start banking snapshots -- and for Japanese sources, snapshots
taken today are the only vintages that will ever exist for today.
"""
