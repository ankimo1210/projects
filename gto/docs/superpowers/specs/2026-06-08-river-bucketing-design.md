# River Hand Bucketing for the Flop Solver — Design (Phase 6 enabler)

Date: 2026-06-08
Status: implemented same day; adversarial review (3 lenses) found one
blocker — unweighted regret aggregation — fixed before any solve shipped.
Review-driven corrections are marked [review] below.
Project: `gto/crates/gto-hu` — extends `FlopSolver`
Parent spec: `2026-06-06-hu-abstract-solver-design.md` §8 (card abstraction
Level 2), §13 Phase 6.

> Goal: make full SRP 100bb flop trees solvable. Exact-combo dense tables
> need 105.35 GB (measured, `solve-hu-flop` rejects them). This document
> picks the abstraction and pins its correctness story.

---

## 1. Why not suit isomorphism

The 22,100→1,755 flop canonicalization works because flops are *free*
variables. Given a FIXED flop, turn/river cards merge only under suit
permutations that map the flop to itself. On the most common flop class —
three distinct ranks, three distinct suits (e.g. AhKd7s) — every suit is
pinned by a distinct rank, the automorphism group is trivial, and **no
turn/river cards merge at all**. Two-tone and monotone flops allow 2–6
automorphisms, but the weighted average saving across canonical flops is
well under 2×. The earlier "3–5×" note in PROGRESS.md was wrong; this
spec supersedes it. Isomorphism is not the lever — hand bucketing is.

## 2. Approach: bucket the STRATEGY SPACE only

Standard lossy card abstraction replaces hands with buckets everywhere
(payoffs included). We do something more conservative, preserving the
solver's correctness story:

- **Traversal stays exact.** Reach vectors, blocker masking, chance
  weights (1/45, 1/44) and showdown payoffs all remain per-combo
  (1326-dim), bit-for-bit the same code paths as today.
- **Only regret/strategy storage is shared.** At a bucketed street, all
  combos in a bucket share one regret/strategy-sum row. Strategy of
  combo c = strategy of `bucket(c)`. This is classic imperfect-recall
  abstraction CFR (regrets aggregate additively across the combos that
  map to the same bucket).
- **Best response stays per-combo and exact.** The BR algorithm walks
  the real game against the bucket-constrained average strategy (the
  average-strategy ACCESSOR changes: it expands K-wide rows to combos).
  [review] The reported number is the exact full-game exploitability of
  the exported profile — an aggregate gap to true equilibrium that
  absorbs abstraction loss AND any update-rule defect; it is not an
  additive decomposition into named terms. "Equilibrium with
  exploitability attached" survives bucketing unchanged.

Memory shrinks by ~N/K on bucketed streets (N=1326); compute per
iteration is unchanged (node strategies expand from K rows in O(K+N)
instead of per-combo regret matching, which is mildly cheaper).

## 3. Bucket definitions

| Street | Context | Bucketing | Default |
|---|---|---|---|
| Flop | 1 | exact combos | exact |
| Turn | 49 | exact combos (tables are small: 49 ctx) | exact |
| River | 49×48 | strength-percentile bins per (turn, river) board | K_r = 128 |

River buckets per context (t, r): rank all combos with
`strength > 0` by `ShowdownTable` strength ascending, then walk in
equal-strength TIER groups; every member of a tier gets
`tier_start_rank * K_r / n_ranked`. [review] The earlier per-position
formula could split a tie across a boundary, violating §6 invariant 2 —
the tier-grouped rule is the implemented one. Board-blocked combos get
bucket 0 and contribute nothing: the update weights them out (§5).
[review] `K_r = N` is real (tier-injective) bucketing, not an exact
fallback — a silent no-op at K=N made the differential test vacuous.

What this abstraction is blind to, by construction: **blocker texture
within a strength tier** (AhKh vs AdKd with equal strength share a
bucket but block different parts of the villain range). The measured
exploitability quantifies exactly this loss; K_r is the dial.

Turn bucketing (mean-river-percentile bins) is specified for later but
NOT implemented now — turn tables are 49/2352 of the problem.

## 4. Storage and memory math

`NodeTable` slabs at river nodes shrink from `na × 1326` to `na × K_r`
f64 entries. Dense-table estimate (the `--max-table-gb` gate) becomes

```
dense = Σ_action_nodes 2 × 8 × ctx_count(street) × na × dim(street)
dim(River) = K_r (when bucketed), else 1326
```

Measured split for SRP 100bb (pot 5bb, stack 97.5bb): 105.35 GB dense
= flop 0.0008 + turn 0.356 + river 104.990 GB (river share 99.66%, 836
river action nodes). [review] The formula is deterministic:
K_r=128 → 10.49 GB, K_r=64 → 5.42 GB. The CLI gate defaults to 8 GB,
so the §6.5 smoke run at K_r=128 must pass `--max-table-gb 11`+.

Bucket maps: `river_bucket[(t,r) pair] : Vec<u16>` shared between
mirrored (t,r)/(r,t) contexts like the showdown tables — 1176 × 1326 ×
2 B ≈ 3 MB. Built once in `FlopSolver::new` from the already-computed
`ShowdownTable`s (needs a `strengths()` accessor).

## 5. Update rules (imperfect-recall CFR)

For a bucketed node with K rows (b = bucket(c)):

- strategy: `σ[a][c] = regret_match(reg[·][b])[a]` — one regret-match
  per bucket, expanded to combos.
- regret update [review — the original unweighted sum was a BLOCKER]:
  `reg[a][b] += Σ_{c∈b} w_c × (action_val[a][c] − ev[c])` where
  `w_c` = the traverser's own deal probability (range weight × board
  mask, i.e. `export_weight`). w_c is the chance part of the
  counterfactual reach π₋ᵢ; per-combo rows hide it by scale invariance,
  shared rows do not. Unweighted, board-blocked combos (showdown value
  exactly 0, fold value negative) teach shared rows that calling is
  free — measured 70× exploitability inflation on a near-lossless map.
  w_c = 0 combos are skipped entirely. CFR+/DCFR discounting applies to
  the shared row once per visit.
- average strategy: `ssum[a][b] += sw × Σ_{c∈b} reach[c] × σ[a][c]`
  (reach = π_i × w_c, already board-masked along the chance path).
- `average_strategy(node, ctx, c)` returns the bucket row normalized.
  [review] This is the bucket-level normalization broadcast to combos,
  NOT each combo's own time-average of behaviour (combos sharing a row
  with diverging reach schedules export the shared mixture). Export and
  BR read the same row, so the exploitability number is consistent with
  what is exported.

Discounting note: buckets are per-context, so a row is updated at most
once per traverser per iteration exactly like an exact-mode slab; the
lazy-discount discipline is genuinely unchanged.

## 6. Validation (mandatory, in test order)

1. **Exact-mode regression**: `buckets_river = 0` (exact) must leave
   every existing flop test green — the abstraction is strictly opt-in.
2. **Bucket-map invariants**: every unblocked combo gets a bucket
   < K_r; monotone in strength (rank_i ≤ rank_j ⇒ bucket_i ≤ bucket_j);
   equal strength ⇒ equal bucket; map shared across mirrored contexts.
3. **Tiny differential vs exact**: on the tiny flop config (2×2 hands),
   bucketed K_r=1326 vs the exact solver — game values within the joint
   exploitability budget. NOTE (self-review correction): buckets are
   GLOBAL strength percentiles over all 1326 combos, so "more buckets
   than live hands" does NOT imply losslessness; and even K=1326 only
   guarantees tier-injectivity (equal-strength combos still share a row
   while their blocker effects may differ). The comparison is therefore
   budget-based, never equality-based.
4. **Abstraction-loss dial**: on a small real config, exact expl(K=4) >
   expl(K=64) after identical training (loose, single seed — guards the
   dial's direction, not a theorem).
5. **Full SRP 100bb smoke**: tree builds, dense estimate under the gate
   at K_r=128, sampled training runs, exact BR completes; expl reported
   and recorded in PROGRESS (no pass/fail threshold — first ever number
   for this tree).

## 7. CLI

`solve-hu-flop --buckets-river K` (default 0 = exact). The summary JSON
gains `"buckets_river": K`; the solver line of PROGRESS must always
quote expl alongside K so abstraction loss is never hidden.

## 8. Risks / accepted limitations

- Imperfect-recall abstraction CFR has no exact convergence theorem;
  the exact BR keeps us honest (worst case: a big expl number tells us
  K was too small).
- Strength-percentile buckets ignore blockers within a tier (accepted —
  measured by expl) and draw/nut structure is irrelevant on the river
  (strength IS the river feature, which is why river-only bucketing is
  the right first step).
- Turn bucketing, bucket-count autotuning, and Phase 6 blueprint glue
  are out of scope here.
