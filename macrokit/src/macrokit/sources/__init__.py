"""Per-source adapters.

Each adapter implements three methods and nothing else:

  probe(indicator)     -- cheapest possible check for "has anything changed"
  fetch_raw(indicator) -- the bytes, exactly as the source served them
  parse(indicator)     -- those bytes as Observation rows

They are deliberately separable. An adapter with `fetch_raw` but no working
`parse` still reaches the `fetching` state, which is enough to start banking
snapshots -- and for Japanese sources, snapshots taken today are the only
vintages that will ever exist for today.
"""
