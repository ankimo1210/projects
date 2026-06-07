# Phase 6 Blueprint — Full-Game HU Solver over an M-Flop Board Abstraction

Date: 2026-06-08
Status: design v2 — adversarial review (3 lenses) found one blocker
(ill-defined flop-deal measure) and three majors; all corrections are
incorporated below, marked [review]. Implementation is the next work
item and must follow THIS version.
Project: `gto/crates/gto-hu` — new `BlueprintSolver`
Parent specs: `2026-06-06-hu-abstract-solver-design.md` §13.6,
`2026-06-08-river-bucketing-design.md`.

> Goal: connect the preflop tree's `NextStreet` leaves to REAL postflop
> subtrees and report a full-game exploitability. This replaces the
> Phase 5 all-in-equity value model for non-all-in leaves.

---

## 1. Scaling reality (why the board must be abstracted)

Per-flop postflop tables at the proven street abstraction
(K_r=128 / K_t exact) cost 10.49 GB; even at an aggressive
K_r=16 / K_t=32 an SRP-sized subgame is ≈ 1.3 GB **per flop**. The
canonical flop set (1,755) is therefore out of reach by ~3 orders of
magnitude in RAM (and the suit-isomorphism lever is dead on rainbow
flops — bucketing spec §1). Real blueprints abstract boards into bucket
transitions; that is a research-scale feature. Phase 6 v0 instead makes
the board abstraction EXPLICIT and small:

**The abstract game deals one of M weighted canonical flops** (M ≈ 3–5,
weights = canonical-class frequencies, renormalized). Within this
M-flop game everything else is the proven machinery: exact-combo
traversal, street bucketing, enumerated/sampled chance, and an exact
best response — so the reported exploitability is exact FOR THE M-FLOP
GAME and is labeled as such. It is NOT full-NLHE exploitability; the
flop sample is the dominant unmodeled abstraction.

## 2. Game composition

```
preflop tree (Phase 5, 15 action nodes, exact-combo rows)
 ├─ FoldTerminal …                       (exact, as today)
 ├─ NextStreet{AllInPreflop}             → M-flop runout value (see §4)
 └─ NextStreet{pot type, pot P, stack S} → Chance(flop: M outcomes, w_m)
        └─ flop subtree m: build_flop_tree(P, S, cfg(pot type))
             with Abstraction{K_r, K_t}  (bucketing specs)
```

[review] **8 subgame families, keyed by preflop LEAF NODE ID** (not by
(P, S)): (2, 99) limped, (5, 97.5) srp, (8, 96) and (12, 94)
limp-raised, (18, 91) 3bet, **two distinct (24, 88) limp-3bet leaves**
(via BB raise-to-4 and raise-to-6 — sharing them would merge infosets
that differ in BB's OWN preflop action, the strongest perfect-recall
violation), (44, 78) 4bet. Configs: `FlopTreeConfig::srp()` for
limped/srp-class pots, `::threebet()` for 3bet pots, and a NEW
`::fourbet()` per parent spec §6 (flop: check/b25/allin; turn, river:
check/allin) for the (44, 78) leaf — no such config exists yet.

## 3. Solver: one end-to-end CFR, not alternating solves

A single `BlueprintSolver` owns the preflop tables plus M × 8 flop
sub-solvers' tables and runs CFR over the whole composed game per
iteration. End-to-end CFR targets the composed abstract game directly;
the alternative (alternate preflop solves against frozen postflop
values) optimizes against stale continuations and was rejected — its
fixed point is not a CFR target of any single game. (Convergence
caveats under bucketing: see the claim-discipline bullet below.)

- Reach entering subgame (m, leaf): preflop reach vector at the leaf ×
  flop-m board mask (zero_card on 3 cards).
- [review — the original weighting was a BLOCKER] **Measure definition.**
  Turn/river chance is exact at constant weight only because every
  (hero, villain) deal has the same legal-card count (45/44). For M
  sampled flops the legal mass Z(h,v) = Σ_{m legal for (h,v)} w_m varies
  per pair and does not factor into per-combo masks; unnormalized
  masking creates a "void game" that subsidizes continuing with
  rep-blocking combos. The blueprint therefore defines the abstract
  game with the JOINT measure
      μ(h, v, m) ∝ w0(h) · w1(v) · w_m · 1[legal(h,v,m)],
  i.e. hand deals occur proportionally to Z(h,v). All flop-entry
  traversal stays exactly as today (per-combo masks, O(N)); the entire
  correction lives in the PREFLOP layer, which already affords O(N²):
  preflop FOLD terminals weight each pair by Z(c,o) inside the opponent
  sum, and the game-value / BR normalizers use
  z = Σ w0·w1·compat(h,v)·Z(h,v). Documented quirk: the hand-deal
  distribution depends on the flop sample — that is what makes the
  measure consistent across fold terminals, betting subgames and all-in
  runouts alike.
- Training: flop deal ENUMERATED over the M flops every iteration
  (M is tiny); turn sampled / river enumerated inside subgames, as
  today.
- Exploitability: full-game exact BR under the SAME μ — the existing
  per-street BR recursions composed the same way (preflop BR walks into
  each (m, leaf) subgame BR with the frozen average strategy), with the
  Z-weighted fold terminals and normalizers. Always reported with M and
  the flop list.
- [review] Claim discipline: CFR over bucketed storage has no
  convergence theorem (bucketing spec §8); turn sampling adds MCCFR
  variance. The summary line must read "CFR profile with exact
  exploitability X bb/hand on the M-flop abstract game", never
  "equilibrium of the abstract game".

## 4. All-in preflop leaves

Valued by the SAME M-flop chance: enumerate flop m → turn → river
showdown (no betting). For consistency the all-in leaf must use the
M-flop runout, NOT the Phase 5 MC equity table — otherwise the two
abstractions disagree about board distribution and the preflop jam
calculus is biased relative to the rest of the game. (Implementation:
reuse the flop solver's all-in chance chain valuation with a betting-
free tree, or close-form via ShowdownTables of the M flops.)

## 5. Memory & compute budget ([review] measured via the dense gate)

Per (leaf, flop) at K_r=16, K_t=32, f64 — measured with the CLI gate
(node counts depend on SPR through raise-ladder truncation, NOT just on
the config; the limped pot is the LARGEST subgame):
- (2, 99) limped 1.90 GB; (5, 97.5) 1.28 GB; (8, 96) 0.97 GB;
  (12, 94) 0.73 GB (srp config)
- (18, 91) 0.19 GB; (24, 88) ×2 ≈ 0.17 GB each (3bp config);
  (44, 78) 0.12 GB (4bp config, NOT negligible)
Per flop Σ ≈ 5.5 GB → M=3 ≈ **17 GB** (fits), M=5 ≈ 28 GB (needs f32
or K_r=8). Side structures (1176 ShowdownTables ≈ 13 MB + bucket maps
≈ 3 MB, ~2 s setup each) MUST be shared per flop across the 8 leaves
(Arc) — they depend only on the board.

Compute ([review] corrected against the measured 0.974 s/iter SRP
baseline, scaling with dense size): ≈ 4.1 s/iter per flop → M=3 ≈
12 s/iter, 1,500 iters ≈ 5 h; M=5 ≈ 20 s/iter ≈ 8.5 h. Exact BR ≈
3.4 min per flop → M=3 ≈ 10 min. First run is an overnight job;
parallelizing (m, leaf) subgame traversals (disjoint tables; rayon)
is the ×8–24 speedup that should land before long runs.

## 6. Validation ([review] rewritten — the original had the same
vacuity traps the bucketing review caught)

0. **Exact-mode regression**: the full existing gto-hu suite stays
   green and a fixed-seed standalone solve-hu-flop run reproduces its
   summary byte-identically — blueprint plumbing must not perturb the
   standalone solvers.
1. **Degenerate composition (M=1, EXACT equality)**: single flop,
   ranges flop-disjoint, Enumerate mode, same variant/iterations →
   game value, exploitability AND per-combo average strategies must
   match the standalone FlopSolver to ~1e-9 (reach multipliers are
   exactly 1.0 on a forced line; Z ≡ w_1 = 1). Budget-form |Δv| ≤
   ε₁+ε₂ assertions are tautologies and are banned as primary checks.
2. **All-in consistency (adversarial fixture)**: M ≥ 2 with NON-uniform
   w_m and at least one combo pair that BLOCKS one of the sampled
   flops; expected values hand-computed under μ (incl. the Z weighting).
   A naive (1/M)Σ-equity implementation must FAIL this fixture.
3. **Chance-math differential**: tiny scalar reference game with a
   dealt-flop stage. The scalar game must implement μ explicitly
   (hand deals reweighted by Z(h,v) — this is the definition the
   vector engine is checked against, so the fixture must include a
   rep-blocking hand and non-uniform w_m, else it degenerates to the
   vacuous case). Compare game values AND exploitability computed by
   the independent scalar BR (validation::exploitability) against the
   composed solver's exact BR — pinning the headline number itself.
4. **Bucketed handoff differential**: M=2 with a real preflop mixed
   line, tier-injective K=N postflop buckets vs exact composition —
   expl difference must be negligible (the regret-aggregation weight
   under preflop reach is exactly the class of bug the bucketing
   review caught at 70× cost).
5. **End-to-end smoke**: M=3, 100bb, short sampled run; expl decreases
   across ≥2 checkpoints; anchor: AA never open-folds; chips conserve
   at every subgame root (pot/stack handoff from the leaf states).
6. **Honesty rails**: summary states "CFR profile with exact
   exploitability X on the M-flop abstract game (flops: …)"; PROGRESS
   quotes expl with M and the flop list.

## 7. Risks / out of scope

- M ≈ 3–5 flops is a DEMO-scale board abstraction; strategy quality on
  unseen flops is undefined (no flop-mapping for play). Real board
  bucketing or disk-backed/f32 tables are future work.
- Imperfect-recall caveats from the bucketing spec carry over.
- Rake remains disabled (parent spec §5).
