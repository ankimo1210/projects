# Mode Matrix Roadmap + M1 (Custom Solve Foundation) — Design

Date: 2026-06-11 (rev 2)
Status: rev 2 after a 59-agent adversarial re-review (workflow `wf_516fbff8-8bf`:
5 lenses — architecture fitness, variant seam, M2 range data, compute budget,
spec critique; 14 findings confirmed, 12 adjudicated, 1 refuted). The user
explicitly authorized decommissioning existing assets where they dead-end.
Spec awaiting user review.
Project: `gto/` — product roadmap toward the full solver mode matrix
Relation to Phase E: **M1 runs before E1**. The E1 spec
(`2026-06-09-phase-e1-public-deploy-design.md`) stays valid for infra/auth but
its feature-gating tables must be revised after M1 (GameSpec becomes the API
contract; `/api/solve` cost tiers are new gating input).

> Goal: support, over time, the full mode matrix —
> Game (Cash/Tournament) × Variant (NLHE/PLO) × Table (HU/6max/9max) ×
> Stack × Rake (site/live/none) × Spot (Preflop/Postflop/Full hand) ×
> Configuration (positions, pot type, board, ranges, action tree) ×
> Output (strategy, EV, equity, range, frequencies, exploitability) —
> within single-GPU (RTX 5080, 16 GB) + desktop-CPU limits, starting with
> what is feasible now.

---

## 1. Structural facts that shape the roadmap

### F1 — "6max/9max postflop" is a 2-player problem
CFR has no Nash-convergence guarantee for 3+ player games. Commercial solvers
ship "6max" as: preflop charts / approximate multiway CFR, plus **postflop
solved as 2-player subgames between position pairs** (SRP, 3bet pot, 4bet
pot), with ranges fixed by the preflop chart. Consequence: the 6max/9max axis
is mostly **preset matrices over the existing HU machinery** — not a new
solver. The hard part is the *range data*, not the solver (§4 M2: today's
chart inventory covers only 7 of the 35 chart objects a full 6max SRP+3bet
matrix needs).

### F2 — HU ICM ≡ chip EV
With 2 players, ICM $EV is linear in stack, so HU tournament differs from HU
cash only by **antes and shallow stacks (10–40bb)**. ICM becomes meaningful
(bubble, FT) only with 3+ players, i.e. coupled to multiway preflop (M3).

### F3 — PLO is ~204× NLHE, and not a pure scale-up
52C4 = 270,725 starting hands vs 1326 (204×). Per-iteration cost is linear in
combo count, so HU PLO **river** is a feasible CPU experiment
(~3.5 min / 2000 iters, ~140 MB — extrapolated from measured NLHE river
1.0 s / 2000 iters). But two things do NOT scale linearly: (a) the blocker
correction — the current showdown sweep uses a per-single-card accumulator
valid only for 2-card hands; 4-card hands need inclusion–exclusion over up to
4 shared cards; (b) the dense N×N equity model used by the preflop/blueprint
value path (270,725² is infeasible — that path is permanently out of PLO
scope). PLO flop/full hand stays a non-goal pending bucketing research.

### F4 — Rake is solver surgery, not a payoff tweak  *(new in rev 2)*
Rake makes the game general-sum, and gto-hu's exploitability machinery
**assumes zero-sum**: payoffs are asserted to sum to 0 and exploitability is
computed as `(BR₀+BR₁)/2`, which under rake understates exploitability by
~rake/2 and trips the assert. The fix: compute per-player **BR gain =
BR_value − game_value(profile)** and report `NashConv = Σᵢ gainᵢ` (this is the
standard ε-certificate for general-sum, so the "equilibrium claim requires
exploitability attached" policy survives — but the formula, the asserts, and
the tests all change). Validation: Kuhn/Leduc with a toy rake, where the
raked equilibrium is hand-checkable.

---

## 2. Asset disposition (decommission / migrate / keep)

User-authorized redesign. Dependency claims below were adversarially verified
against routers (`src/gto/api/routers/*`) and web pages.

### Decommission in M1 (dead branch — zero API/page breakage)
The "approximation multistreet" middle tier is reachable from **no API router
and no web page**, only from two offline batch scripts, and is qualitatively
superseded by gto-hu turn_river/flop:
- `crates/gto-core/src/multistreet.rs` (solve_multistreet, SubgameSolver)
- gto-py `solve_spot_multistreet` binding
- `src/gto/solver/multistreet_gpu.py`
- `src/gto/library/batch_multistreet.py`, `_sample_multistreet.py`
- the `solutions_ms` Parquet store (+ their tests)

Note: this tier received correctness fixes in the 2026-06-11 sweep (B5, B10);
those fixes are preserved in git history. Retiring fixed code is deliberate —
it was repaired to understand it, and it is still the wrong foundation.

### Migrate in M2 (live but wrong-engine surfaces)
- `POST /api/solver/solve` (/solver page) and the postflop branch of
  `POST /api/simulation/run` (/simulation page) currently run on **gto-cuda
  single-street** (flop = call→showdown — qualitatively wrong flop
  incentives). Rebuild both on gto-hu via the new `/api/solve`.
- The 19,305-spot gto-cuda library is **demoted to a labeled instant-preview
  tier** (`equilibrium_claim=false` in the envelope, visible "approximation"
  label in UI). Fact found in review: the library is solved with **uniform
  ranges** (`batch.py` never passes `ip_weights`/`oop_weights`), so its
  position labels differ only via pot size. M2 either wires real chart
  weights into the regen (cheap: one ~53 min regen) or keeps the uniform
  label honest. Do **not** extend this library to 3bet pots — single-street
  call→showdown is at its worst at low SPR; any 3bet-pot tier comes from
  gto-hu.
- After migration, retire `gto-core` cfr.rs single-street `solve_spot` (today
  it survives only as the CPU exception-fallback under two gto_cuda call
  sites).

### Keep (carries to the matrix)
- **gto-hu** — the backbone; every matrix row ultimately lands here.
- `/api/hu/*` + /hu page — the only equilibrium-grade surface today;
  **subsumed** by `/api/solve` in M1 (alias, deprecate, fold the /hu page
  into the Custom Solve UI) so two parallel HU surfaces don't persist.
- Trainer hardcoded charts (`preflop_data.py`) — the M2 range-data seam.
- Review parser — orthogonal; its parsed real-hand rake values are a free
  cross-check for RakeModel presets.
- `range_builder` / `flop_canon` / Parquet store / web shell.
- gto-cuda — instant-preview tier only (river-only solves remain correct);
  its NVRTC/FFI infra is a potential reuse for the M3/M4 GPU experiment.
- Legacy request/response schemas (`SolveRequest`, `SimRequest`,
  `RiverRequest`...) are frozen-deprecated; `/api/solve` (GameSpec) is
  greenfield and `GET /api/solve/capabilities` is the single source of truth
  for the supported sub-matrix.

---

## 3. Phases

### M1 — Custom Solve foundation (HU NLHE cash). Two milestones:
- **M1a (sync tier)**: GameSpec + capabilities, rake (incl. the F4
  exploitability rework), range/bet-size inputs on river + turn_river
  bindings, unified SolveResult, Custom Solve web form, decommission list
  above. Compute: zero.
- **M1b (async tier)**: NEW `solve_hu_flop` pyo3 binding (none exists today
  — only river/turn_river are registered), minimal in-process job subsystem,
  flop custom solves end-to-end. M1a ships without M1b if needed.

### M2 — 6max position-pair matrix v1 + Tournament-HU (6max first)
Range data is the critical path, not solver work:
- Chart inventory today: 5 RFI + 2 BB-defend (BB_vs_BTN, BB_vs_CO) = 7 of the
  35 chart objects a full 6max SRP+3bet matrix needs (15 position pairs ×
  {defend, opener-vs-3bet} + 5 RFI) — an **80% gap**, and 0/15 on the 3bet
  side.
- **M2 v1 scope = BB-as-sole-defender**: ship {UTG,HJ,CO,BTN,SB}-vs-BB SRP +
  the same five 3bet pots. Needs ~8 new charts (3 missing BB-defends + 5
  opener-vs-BB-3bet) — hand-checkable against published 6max ranges. Add a
  consistency validator (defend-chart 3bet frequency must reconcile with the
  paired opener-vs-3bet chart). Prefer importing a vetted published chart set
  over hand-typing; never source charts from gto-hu's preflop value model
  (realization=1 all-in model — documented as unsuitable); blueprint-sourced
  charts are HU-only and gated on M3 quality.
- The remaining 14 pairs (20 charts) defer to M3.
- 3bet-pot postflop tier: on-demand gto-hu turn+river with a persistent
  result cache (not a gto-cuda batch).
- Tournament-HU: ante/BB-ante + shallow-stack grids (10–40bb).
- 9max = 8 RFI seats, 36 pairs / 72 configs — chart authoring only, no new
  solver work.
- Experiment line: intra-solve CPU parallelism (rayon over the 44–48
  independent river contexts in turn_river/flop). Honest cost note: the
  traversal holds `&mut self` shared state, so this is a restructuring, not
  an annotation; potential ~10× on a 20-core CPU if it lands.

### M3 — Preflop true solve / Full hand productization (+ ICM spots)
- HU blueprint quality (larger M, card bucketing) and web exposure.
- 6max preflop MCCFR blueprint experiment: hours-to-tens-of-hours CPU,
  go/no-go by measurement; do a tree-size/memory estimate (169-hand × seats ×
  raise-tree infosets) **before** committing.
- ICM presets (bubble, FT) on top of multiway preflop, if it lands.
- GPU go/no-go: **if** M3 quality goals demand faster flop solves, port the
  gto-hu inner loops to GPU reusing gto-cuda's NVRTC/FFI shell — but NOT its
  O(N²) showdown kernel; the O(N) two-sweep must become a segmented scan.
  Sequenced after the CPU-parallelism experiment proves the decomposition.

### M4 — PLO experiment track
- Implement the PokerVariant trait for PLO **including** the runtime-length
  range refactor (`[f64; 1326]` → length-checked `Vec<f64>` on the vector
  solvers) and k-card blocker inclusion–exclusion; re-validate bit-identical
  NLHE before/after.
- HU PLO river prototype (~3.5 min / 2000 iters CPU expected); measure, then
  go/no-go.

### Non-goals (explicit, all phases)
3+ player simultaneous-equilibrium postflop; PLO flop/full hand without a
bucketing result; 9max preflop true solve; PLO genericity for the N×N equity
model / blueprint value path (quadratic memory — permanently separate).

---

## 4. M1 design

### 4.1 GameSpec — the API contract for the whole matrix

```jsonc
// POST /api/solve
{
  "game":    "cash",                 // "cash" | "tournament"
  "variant": "nlhe",                 // "nlhe" | "plo"
  "table":   "hu",                   // "hu" | "6max" | "9max"
  "stack_bb": 100.0,
  "rake":    { "model": "site" },    // "none" | "site" | "live" | {pct, cap_bb}
  "spot":    "postflop",             // "preflop" | "postflop" | "full_hand"
  "config": {
    "positions": ["BTN", "BB"],
    "pot_type":  "srp",              // preset id: "srp" | "3bet" | "4bet" | "custom"
    "pot_bb":    6.5,                // ALWAYS present; presets only provide the default
    "board":     ["Ah", "Kd", "7s", "2c", "9h"],   // 3/4/5 cards
    "ranges":    { "ip": "preset", "oop": "preset" },  // preset | notation | weight vector
    "action_tree": { "bet_sizes_pct": [50], "max_raises": 1 },  // null = solver default
    "abstraction": { "buckets_river": 128, "buckets_turn": 0 }  // flop solves only
  },
  "iterations": 2000                 // server clamps per street (see 4.4)
}
```

Rev-2 corrections (from review):
- **`pot_bb` is always required.** The engine takes pot as an independent
  input; `pot_type` presets select a (pot default, bet-size config, range
  preset) row from a documented preflop-line table — they do not compute pot.
  "limped" is dropped (no engine config exists for it; add later with its
  line definition if wanted).
- **`abstraction` block added** — flop solves are bucketed
  (`buckets_river`/`buckets_turn`); GameSpec must express it and SolveResult
  must echo it (4.5).
- Ranges: hand-notation grammar (`"AA,AKs:0.5,KQo"`) via
  `range_builder.hand_to_combo_indices`, or a raw weight vector (length = the
  variant's combo count). Normalized server-side; blocked combos zeroed
  against the board (B6 validation).
- `GET /api/solve/capabilities` returns the supported sub-matrix + per-street
  iteration clamps + cost class (sync/sync-capped/async). M1 supports:
  `cash × nlhe × hu × any stack × {none,site,live} × postflop`.

### 4.2 Rake model + exploitability rework (F4)

`RakeModel { pct, cap_bb, no_flop_no_drop }` applied at terminal payoffs.
Presets in one documented table: `none` 0%/0bb; `site` 5%, 3bb cap, NFND;
`live` 10%, 5bb cap, drop always.

Required solver changes (this is the real M1a Rust work):
1. Terminal payoffs subtract rake (showdown and called pots; fold pots per
   NFND flag).
2. Exploitability: per-player `gainᵢ = BR_valueᵢ − game_valueᵢ(profile)`;
   report both gains + `NashConv`; keep the bb/hand convention as
   `NashConv/2` for continuity. Remove/relax the zero-sum payoff asserts on
   the raked path.
3. Tests: Kuhn + rake (hand-checkable), Leduc + rake; property: rake=0
   reproduces current results bit-identically; raked equilibria show the
   expected direction (less thin value / fewer bluffs).
4. Cross-check data source: the review parser already extracts real rake from
   imported hand histories.

### 4.3 PokerVariant trait seam (PLO prep — thin seam ONLY)

Rev-2 corrections: the seam concerns live in **gto-core** (`range.rs` owns
NUM_COMBOS/combo_index/Range; `eval.rs` owns showdown strengths), so the
trait is defined in gto-core and consumed by gto-hu. Named `PokerVariant`
(NOT `Variant` — that collides with gto-hu's `CfrVariant`, the CFR-algorithm
enum). Shape (review-validated):

```rust
trait PokerVariant {
    type HoleCards;                       // NLHE: (u8, u8); PLO: [u8; 4]
    fn combo_count(&self) -> usize;       // runtime, NOT const-generic
    fn combo_cards(&self, i: usize) -> Self::HoleCards;
    fn blocker_mask(&self, h: &Self::HoleCards) -> u64;   // card bitmask
    fn showdown_strengths(&self, board: &[u8]) -> Vec<u16>;
}
```

**M1 scope is the thin seam**: route combo-count / combo→cards / blocker /
strength lookups through the trait with NLHE as the only impl. The REAL
PLO-blocking work — converting `Range { weights: [f64; 1326] }` and ~90
`[f64; N]` hot-path arrays across 7 solver files to runtime-length vectors,
plus the k-card blocker inclusion–exclusion — is **explicitly M4 scope**,
gated on the PLO go/no-go. The seam is bounded to the river/turn_river/flop
vector solvers; the N×N equity-model path is out (F3).

Acceptance (replaces the rev-1 "no 1326 literal" criterion, which tested the
wrong thing — only 7 doc-comment occurrences exist): (a) existing gto-hu
suite bit-identical; (b) no *behavioral* use of gto-core combo/strength/blocker
functions outside the trait path in the three vector solvers; `NUM_COMBOS` may
remain only as the `const N` array-dimension alias (the thin-seam boundary —
array-type genericity is M4 scope); (c) combo count / combo→cards /
blocker test / strengths reached only via the trait in the three vector
solvers. Python side is NOT seamed in M1 (its 1326 duplication is recorded
as M4 scope).

### 4.4 Solver bindings, latency tiers, job subsystem

Bindings (all with `py.allow_threads` + overlap validation):
- Extend `solve_hu_river` / `solve_hu_turn_river`: range weights/notation,
  bet sizes, rake. (Range input is a **precondition** of GameSpec `ranges` —
  today the bindings accept none.)
- **NEW `solve_hu_flop`** (M1b): no flop binding exists today (CLI only).
  Signature surfaces `Abstraction{buckets_river, buckets_turn}`.

Latency tiers (measured, drives the interaction model):

| Street | Quality point | Wall | Memory | Tier |
|---|---|---|---|---|
| river | 2000 iters, expl ~0.001 bb | ~1.0 s | ~5 MB | sync (clamp ~10k) |
| turn+river | 10k iters, expl 0.33 bb | ~37 s | 172 MB | sync-capped (iteration cap, not time); presets `fast` 3k ≈ 8 s rough / `standard` 10k; async optional |
| flop (K_r=128) | 3k iters, expl ~1.2 bb | ~49 min | 10.5 GB | async-only |

Honesty notes baked into the API: single-solve latency is single-thread-bound
(CFR loop has no intra-solve parallelism today); turn+river at 37 s flirts
with proxy timeouts — E1's gating revision must account for it; flop output
at K=128/3k iters is approximation-grade (expl ~1.2 bb) until M3 quality
work — `meta.abstraction` + the expl number label it.

Job subsystem (M1b — none exists today; the API has only a 2-worker
ThreadPoolExecutor): minimal in-process design — job id, status endpoint,
persisted result with TTL, cancel; concurrency limits with per-job memory
accounting (flop: at most `floor(free_RAM / 12 GB)` concurrent, i.e. 1 on
this box; bounded executor for turn+river). No external broker.

Web: /solver page grows the Custom Solve form driven by `capabilities`
(board picker, range editor + presets, bet sizes, rake dropdown, street-aware
sync/async UX). /hu folds in (§2).

### 4.5 Unified SolveResult — with field provenance

```jsonc
{
  "strategy":      [...],
  "combo_strategies": [...],
  "ev":        { "ip": ..., "oop": ..., "per_combo": [...] },
  "equity":    { "ip": ..., "oop": ... },
  "ranges":    { "ip": [...], "oop": [...] },
  "frequencies": {...},
  "exploitability": { "nashconv_bb": ..., "per_hand_bb": ...,
                      "br_gain_ip": ..., "br_gain_oop": ... } | null,
  "meta": { "solver": "gto-hu", "iterations": ..., "elapsed_s": ...,
            "abstraction": null | {"buckets_river": ..., "buckets_turn": ...},
            "rake": {...}, "equilibrium_claim": bool }
}
```

Provenance (rev 2 — each field's source is specified, not assumed):
`ev` ← solver game_value; `per_combo` ← average-strategy combo values;
`equity` ← a **separate** server-side range-vs-range equity computation (not
a solver output); `ranges` ← echo of post-normalization inputs;
`exploitability` ← the F4 general-sum formulas. Tiers that lack a field
return `null` (the gto-cuda preview tier: `exploitability: null`,
`equilibrium_claim: false`). `equilibrium_claim` stays true only for gto-hu
with exploitability attached — including bucketed flop solves, whose expl
number already contains the abstraction loss (meta.abstraction ≠ null makes
the trade visible).

### 4.6 M1 acceptance criteria (rev 2)

**M1a**
1. `POST /api/solve` solves HU NLHE cash postflop for river and turn+river
   with custom board/ranges/bet-sizes/stack/rake; unsupported GameSpec
   combinations 422 with reason + capabilities pointer.
2. Rake: rake=0 path bit-identical to current results; Kuhn/Leduc+rake tests
   pass with hand-checked values; raked solve reports general-sum
   exploitability (per-player BR gains) without tripping asserts.
3. PokerVariant seam: criteria (a)–(c) of §4.3.
4. Decommission list removed; full cargo + pytest green afterwards; `/api`
   surface unchanged except deprecation headers on `/api/hu/*`.
5. Two concurrent turn+river solves overlap (B4); bounded executor enforces
   the concurrency cap (note: this is throughput — single-solve latency is
   unchanged by design).

**M1b**
6. `solve_hu_flop` callable from Python; flop job submit→status→result flow
   works end-to-end with `meta.abstraction` populated; job memory cap
   enforced (second concurrent flop job queues, not OOMs).
7. Web Custom Solve form renders results for all three streets with honest
   quality labels (expl + abstraction badge).

---

## 5. Decision log

- 2026-06-11 (user): **M1 before E1**; E1 spec revised after M1.
- 2026-06-11 (user): **6max before Tournament-HU** within M2.
- 2026-06-11 (user): **PLO = trait seam only** in M1; implementation deferred
  to M4 experiment.
- 2026-06-11 (user): **decommission/redesign authorized** where assets
  dead-end → §2 disposition adopted (multistreet approximation tier removed
  in M1; gto-cuda demoted to preview tier; /solver & /simulation migrate to
  gto-hu in M2).
- 2026-06-11 (rev 2 adjudications): rake = solver surgery (F4, was
  "terminal-payoff tweak"); pot_bb always required; flop bucketing in
  GameSpec; trait renamed PokerVariant, lives in gto-core, thin-seam-only
  with array-genericity deferred to M4; M2 v1 = BB-as-sole-defender (8 new
  charts) with consistency validator; library uniform-range fact disclosed;
  no gto-cuda 3bet extension; GPU port = M3 go/no-go after CPU-parallelism
  experiment (reuse FFI shell, not the O(N²) showdown kernel).
- Standing: gto-hu is the only equilibrium-claiming solver (with
  exploitability attached); machine-readable as `equilibrium_claim`.
