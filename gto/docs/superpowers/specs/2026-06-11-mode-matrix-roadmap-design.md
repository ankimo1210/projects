# Mode Matrix Roadmap + M1 (Custom Solve Foundation) — Design

Date: 2026-06-11
Status: approved in brainstorm (user picked: M1 before E1; 6max first in M2;
PLO trait-seam only). Spec awaiting user review.
Project: `gto/` — product roadmap toward the full solver mode matrix
Relation to Phase E: **M1 runs before E1**. The E1 spec
(`2026-06-09-phase-e1-public-deploy-design.md`) stays valid for infra/auth but
its feature-gating tables must be revised after M1 lands (custom solve becomes
a gated live feature; GameSpec becomes the API contract).

> Goal: support, over time, the full mode matrix —
> Game (Cash/Tournament) × Variant (NLHE/PLO) × Table (HU/6max/9max) ×
> Stack × Rake (site/live/none) × Spot (Preflop/Postflop/Full hand) ×
> Configuration (positions, pot type, board, ranges, action tree) ×
> Output (strategy, EV, equity, range, frequencies, exploitability) —
> within single-GPU (RTX 5080, 16 GB) compute limits, starting with what is
> feasible now.

---

## 1. Structural facts that shape the roadmap

These three facts decide what is cheap, what is expensive, and what is
impossible on this hardware. They are the reasoning behind the phase cut.

### F1 — "6max/9max postflop" is a 2-player problem
CFR has no Nash-convergence guarantee for 3+ player games. Commercial solvers
(GTO Wizard et al.) ship "6max" as: preflop charts / approximate multiway CFR,
plus **postflop solved as 2-player subgames between position pairs** (SRP,
3bet pot, 4bet pot), with ranges fixed by the preflop chart. Consequence: the
6max/9max axis is mostly **preset matrices (position pair × pot type ×
ranges) over the existing HU machinery** — not a new solver. gto-hu and the
library pipeline are reusable nearly as-is.

### F2 — HU ICM ≡ chip EV
With 2 players, ICM $EV is linear in stack, so HU tournament differs from HU
cash only by **antes and shallow stacks (10–40bb)** — not by a utility
transform. ICM becomes meaningful (bubble, final table) only with 3+ players,
i.e. it is coupled to the multiway-preflop problem. Therefore the Tournament
axis splits: ante + shallow-stack support early (cheap), ICM spots late
(gated on multiway preflop, M3).

### F3 — PLO is ~204× NLHE
52C4 = 270,725 starting hands vs 1326 (204×). Range vectors, strategy
storage, and the showdown sweep all scale with it; the evaluator needs the
exactly-2-of-4 rule and blocker correction needs inclusion–exclusion over up
to 4 shared cards. Feasible on 16 GB: **HU PLO river experiments**. Not
feasible without bucketing research: PLO flop / full hand. Decision (user):
in M1 we only cut the **Variant trait seam** so PLO can be slotted in later;
no PLO implementation before M3+.

### Rake note (correctness)
Rake makes the game general-sum. CFR self-play still works in practice and —
because gto-hu computes **exact best responses** — the per-player BR gains
remain a valid ε-certificate (sum of BR gains bounds the distance from
equilibrium in general-sum games too). The "equilibrium claim requires
exploitability attached" policy survives rake unchanged.

---

## 2. Current state vs target matrix

| Axis | Today | Target (phase) |
|---|---|---|
| Game | Cash only | + ante/shallow (M2), ICM spots (M3) |
| Variant | NLHE | trait seam (M1), HU PLO river experiment (M3+/M4) |
| Table | HU exact (gto-hu); position-vs-BB flop library | 6max pair matrix (M2), 9max positions (M2, same machinery) |
| Stack | 50/100/200 library; gto-hu parametric | arbitrary via custom solve (M1), grid extension (M2) |
| Rake | none (parser reads rake for review only) | none/site/live in gto-hu terminals (M1) |
| Spot | Postflop exact (HU river/turn+river/flop); preflop = hardcoded charts; HU blueprint (rough) | custom postflop web (M1), preflop/full-hand productized (M3) |
| Configuration | board via CLI; ranges partially (pyfunction weights); fixed bet sizes | full custom config via GameSpec API (M1) |
| Output | strategy/equity/freqs; expl (gto-hu); EV (root_ev) | unified SolveResult schema everywhere (M1) |

---

## 3. Phases

### M1 — Custom Solve foundation (HU NLHE cash, all Configuration + Output)
Compute: ~zero (on-demand solves only). Detailed design in §4.

### M2 — 6max/9max position-pair matrix + Tournament-HU (6max first)
- Position pair × pot type (SRP/3bet, then 4bet) preset matrix; preflop
  ranges from extended charts (chart upgrade, not a solve).
- Library regeneration on the extended grid (GPU, hours — single batch run).
- Ante/BB-ante support + shallow-stack grids (10–40bb) = Tournament-HU.
- 9max = more positions in the same matrix; no new solver work.

### M3 — Preflop true solve / Full hand productization (+ ICM spots)
- HU blueprint quality (larger M, card bucketing) and web exposure.
- 6max preflop MCCFR blueprint experiment with a simple multiway value
  model — the compute wall lives here; go/no-go by measurement.
- ICM presets (bubble, FT) on top of multiway preflop, if it lands.

### M4 — PLO experiment track
- Implement the Variant trait for PLO (evaluator, 270,725-combo ranges,
  blocker sweep); HU PLO river prototype; measure memory/speed; go/no-go.

### Non-goals (explicit, all phases)
- 3+ player simultaneous-equilibrium postflop (no theoretical guarantee,
  no compute headroom).
- PLO flop / full hand without a bucketing result.
- 9max preflop true solve.

---

## 4. M1 design

### 4.1 GameSpec — the API contract for the whole matrix

One request schema covers every current and future mode. Unsupported
combinations are rejected eagerly with a machine-readable reason, so the
matrix can grow without breaking the contract.

```jsonc
// POST /api/solve
{
  "game":    "cash",                 // "cash" | "tournament"
  "variant": "nlhe",                 // "nlhe" | "plo"
  "table":   "hu",                   // "hu" | "6max" | "9max"
  "stack_bb": 100.0,                 // effective stack, arbitrary float
  "rake":    { "model": "site" },    // "none" | "site" | "live" | custom {pct, cap_bb}
  "spot":    "postflop",             // "preflop" | "postflop" | "full_hand"
  "config": {
    "positions": ["BTN", "BB"],      // table-dependent position names
    "pot_type":  "srp",              // "srp" | "3bet" | "4bet" | "limped" | "custom"
    "pot_bb":    null,               // required iff pot_type == "custom"
    "board":     ["Ah", "Kd", "7s", "2c", "9h"],  // 0/3/4/5 cards by street
    "ranges":    { "ip": "preset", "oop": "preset" },  // "preset" | weights[1326] | notation
    "action_tree": { "bet_sizes_pct": [50], "max_raises": 1 }  // null = solver default
  },
  "iterations": 2000                 // optional; server clamps
}
```

- `GET /api/solve/capabilities` returns the supported sub-matrix (per-axis
  values + valid combinations), so the UI greys out unimplemented modes and
  the 422 contract is discoverable. M1 supports exactly:
  `cash × nlhe × hu × any stack × {none,site,live} × postflop ×
  {river, turn_river, flop} boards`.
- Range notation accepts the existing hand-string grammar
  (`"AA,AKs:0.5,KQo"`) via `range_builder.hand_to_combo_indices`, or a raw
  weight vector (length = the variant's combo count; 1326 for NLHE). Both
  normalize server-side; blocked combos are zeroed against the board
  (B6-style validation applies).
- Everything is centi-bb integers inside gto-hu, floats at the API edge
  (existing convention).

### 4.2 Rake model (gto-hu terminals)

`RakeModel { pct: f64, cap_bb: f64, no_flop_no_drop: bool }` applied at
terminal payoff computation: showdown pots and called-fold pots pay
`min(pot * pct, cap)` out of the pot before payoff. Presets are constants in
one table, documented by the API: `none` = 0%/0bb; `site` = 5%, 3bb cap,
no-flop-no-drop; `live` = 10%, 5bb cap, drop always. Exact BR runs on the
raked game, so exploitability stays exact for the game actually solved
(see §1 rake note).

### 4.3 Variant trait seam (PLO prep, no PLO)

In gto-hu, isolate behind one trait what PLO would change:
`combo count`, `combo→cards mapping`, `showdown_strengths(board)`,
`blocker overlap test`. NLHE is the only implementation in M1. Acceptance:
no behavior change (existing tests bit-identical) and no `1326` literal left
on solver hot paths outside the NLHE variant impl.

### 4.4 Solver bindings + web exposure

- Extend pyo3 bindings: `solve_hu_river` / `solve_hu_turn_river` (+ flop)
  accept ranges, bet sizes, rake; all keep `py.allow_threads` (B4) and
  card-overlap validation (B6).
- New router `POST /api/solve` (GameSpec) delegating to the right gto-hu
  entry; `turn_river` and `flop` join `river` on the web (executor-based,
  B4 makes this real concurrency). Cost reality drives the interaction
  model: river ≈ seconds (synchronous), turn+river ≈ 30–40 s (synchronous
  with cap), flop = minutes even river-bucketed → **async job** (submit →
  poll/notify) with iteration/bucketing caps. This is the local/dev
  surface — public gating is E1's job (E1 spec revision will classify
  `/api/solve` cost tiers).
- Web `/solver` page grows a Custom Solve form driven by `capabilities`
  (board picker, range editor textarea + presets, bet-size input, rake
  preset dropdown).

### 4.5 Unified SolveResult (Output axis)

Every solve endpoint returns the same envelope:

```jsonc
{
  "strategy":      [...],            // per root action: {action, freq}
  "combo_strategies": [...],         // per combo per action (range view)
  "ev":            { "ip": ..., "oop": ..., "per_combo": [...] },
  "equity":        { "ip": ..., "oop": ... },
  "ranges":        { "ip": [...], "oop": [...] },   // post-normalization inputs
  "frequencies":   {...},            // aggregate action frequencies
  "exploitability": { "total_bb": ..., "br_ip": ..., "br_bb": ... } | null,
  "meta": { "solver": "gto-hu", "iterations": ..., "elapsed_s": ...,
            "abstraction": null | {...}, "equilibrium_claim": bool }
}
```

`equilibrium_claim` is true only for gto-hu results with exploitability
attached (existing policy, now machine-readable). Library/approximation
endpoints adopt the envelope with `exploitability: null`.

### 4.6 M1 acceptance criteria

1. `POST /api/solve` solves HU NLHE cash postflop for river, turn+river, and
   flop boards with custom board/ranges/bet-sizes/stack/rake; unsupported
   GameSpec combinations 422 with reason + capabilities pointer.
2. Rake changes the solution (regression test: raked vs unraked equilibria
   differ in the expected direction — less thin value/bluffing) and
   exploitability stays exact on the raked game.
3. Variant trait refactor is bit-identical on the existing gto-hu suite.
4. Web Custom Solve form renders results (strategy grid + expl banner) for
   all three streets; two concurrent solves overlap (B4 verified at API).
5. Full cargo + pytest suites green; new behavior covered by tests that fail
   without it.

---

## 5. Decision log

- 2026-06-11 (user): **M1 before E1**; E1 spec revised after M1.
- 2026-06-11 (user): **6max before Tournament-HU** within M2.
- 2026-06-11 (user): **PLO = trait seam only** in M1; implementation
  deferred to M3+ experiment.
- Standing: gto-hu is the only equilibrium-claiming solver (with
  exploitability attached); gto-core/gto-cuda stay approximation/library
  paths.
