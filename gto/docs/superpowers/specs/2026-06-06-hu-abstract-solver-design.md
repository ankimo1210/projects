# HU NLHE 100bb Abstract Equilibrium Solver — Design

Date: 2026-06-06
Status: approved (design review with user)
Project: `gto/` — new crate `crates/gto-hu/`

> **This is an abstract HU NLHE equilibrium solver, not an unabstracted full
> GTO solver.** All abstractions (action sizes, max raises, board/card
> abstraction, sampling) are explicit and listed in this document.

---

## 1. Goal

Redesign the gto project toward a preflop-to-river abstract GTO solver for
heads-up No-Limit Hold'em cash:

- HU NLHE cash, 100bb effective, SB/Button vs BB
- Preflop (including limp) → Flop → Turn → River
- Fixed action abstraction, CFR+ / DCFR, public chance sampling
- Average strategy output, best response / exploitability measurement
- Rake: disabled initially, configurable later
- The existing single-street flop solver is demoted to river-only /
  terminal-evaluator use. It must never be called GTO for flop/turn.

Correctness first. GPU optimization and GUI are explicitly out of scope until
the CPU core is validated.

## 2. Existing-code audit (summary)

Findings that drive this design (audited 2026-06-06):

| # | Issue | Location |
|---|---|---|
| 1 | `NextStreet` evaluated as Showdown (forbidden flop-call→showdown shortcut) | `gto-core/src/cfr.rs:119-122` |
| 2 | Phantom `2c` bug root cause: `[0u8;7]` zero-padded board passed to `evaluate7` for 3-4 card boards (0 = 2c, duplicated) | `gto-core/src/cfr.rs:188-194`, `multistreet.rs:179-185` |
| 3 | Straight-flush miss: `best5_from_flush_mask` keeps only top-5 ranks of the flush suit, missing SFs formed by lower cards (incl. wheel SF) | `gto-core/src/eval.rs:227-235` |
| 4 | Multistreet backward induction solves turn/river subgames with re-derived **uniform** ranges, not line-conditioned reach ranges | `gto-core/src/multistreet.rs:316-342` |
| 5 | "Exploitability" is a positive-regret proxy, not best response | `gto-core/src/multistreet.rs:252-261` |
| 6 | Average-strategy accumulation weighted by traverser reach instead of actor reach | `gto-core/src/cfr.rs:170` |
| 7 | Kuhn CFR test is a self-contained local implementation; it does not exercise production solver code | `gto-core/tests/kuhn_cfr.rs` |

Reusable assets: card/combo encoding (`rank*4+suit`, 1326 combos), range +
blocker handling, eval LUT (after fix #3), per-combo vector CFR skeleton,
the exact Kuhn best-response logic (as a template).

## 3. Decisions made with the user

1. **Existing web app keeps working.** New solver lives in a new crate
   `crates/gto-hu/`. `gto-core` receives surgical bug fixes only (#2, #3 +
   doc warnings for #1). `gto-py` API unchanged. `gto-cuda` untouched.
2. **Rust core + pyo3 later.** Core, tree, solver, validation, experiments,
   CLI all in Rust. Python bindings once the core is validated.
3. **Two-layer solver core:**
   - **Scalar reference engine**: generic `Game` trait + full-traversal
     CFR/CFR+/DCFR. Runs Kuhn, Leduc, and tiny poker (restricted combo sets).
   - **Vector production engine**: 1326-combo simultaneous traversal for HU
     NLHE with range-reach vectors and chance sampling.
   - Both share regret-matching / discount / averaging primitives.
   - **Differential testing is mandatory**: on tiny river spots (2-6 combos)
     both engines must converge to the same strategy and EV.

## 4. Crate layout

```
gto/crates/gto-hu/
├── Cargo.toml            # deps: gto-core (eval/card), thiserror, rayon (later)
├── configs/
│   └── hu_100bb_limp.json    # full-game tree config (Phase 5+)
├── src/
│   ├── lib.rs
│   ├── cards/            # deck.rs (dead-card tracking), canonical.rs (Phase 4+)
│   ├── game/             # action.rs, betting.rs, state.rs, street.rs,
│   │                     # pot_type.rs, terminal.rs
│   ├── tree/             # config.rs, builder.rs, node.rs, info_set.rs
│   ├── ranges/           # range.rs (1326 weights, blockers, reach update)
│   ├── solver/           # regret.rs, variant.rs, scalar.rs, vector.rs,
│   │                     # sampling.rs, average.rs, rng.rs (SplitMix64)
│   ├── games/            # kuhn.rs, leduc.rs, tiny_river.rs (Game impls)
│   ├── validation/       # best_response.rs, exploitability.rs, sanity.rs
│   ├── reports/          # tree_stats.rs, solver_stats.rs, export.rs (CSV/JSON)
│   └── bin/
│       ├── solve_river.rs        # → solve-hu-river        (Phase 2)
│       ├── solve_turn_river.rs   # → solve-hu-turn-river   (Phase 3)
│       ├── solve_flop.rs         # → solve-hu-flop         (Phase 4)
│       ├── solve_preflop.rs      # → solve-hu-preflop      (Phase 5)
│       └── solve_full.rs         # → solve-hu-full         (Phase 6)
└── tests/
    ├── test_cards.rs  test_betting.rs  test_terminal_payoff.rs
    ├── test_cfr_kuhn.rs  test_cfr_leduc.rs
    ├── test_river_solver.rs  test_best_response.rs
    └── test_differential.rs
```

Mapping from the requested layout: `src/core/*` → crate modules,
`src/experiments/*` → `src/bin/*` (cargo binaries), `src/reports/*` →
`reports` module writing to `~/projects/_data/gto/hu/` (gitignored).

## 5. Chip accounting and betting (game/)

- Chip unit: **i64 centi-bb** (1bb = 100, SB posts 50, BB posts 100,
  stack = 10_000). No floating point in accounting.
- Bet sizes are **committed totals** (`Bet { to }`, `Raise { to }`,
  `AllIn { to }`), never increments (spec requirement).
- `BettingState` tracks: `pot`, `stacks[2]`, `street_committed[2]`,
  `contrib_total[2]`, `to_act`, `raises_this_street`, all-in flags.
- **Payoff convention** (fixes the ±pot/2 error for asymmetric blinds):
  `payoff(p) = chips_won(p) − contrib_total(p)`, reported in bb.
  Zero-sum and pot-conservation are enforced by tests.
- Legal actions are generated from state + config; all-in caps at effective
  stack; illegal actions are structurally impossible (debug_assert guards).
- Rake: `RakeConfig { pct, cap }` plumbed through terminal evaluation,
  fixed at zero initially. No rake logic beyond the hook until the no-rake
  solver is validated.

## 6. Action abstraction (fixed, explicit)

### Preflop (SB/Button acts first)

| Situation | Options |
|---|---|
| SB initial | fold, limp, raise to 2.5bb |
| BB vs limp | check, raise to 4bb, raise to 6bb |
| SB vs BB raise after limp | fold, call, 3bet to 12bb, jam |
| BB vs SB open 2.5bb | fold, call, 3bet to 9bb |
| SB vs BB 3bet | fold, call, 4bet to 22bb, jam |
| BB vs SB 4bet | fold, call, jam |
| Facing jam | fold, call |

Preflop terminals: fold awards pot with exact accounting; call/check
proceeds to flop with correct pot/stacks and a pot-type tag.

### Postflop, by pot type

Pot types: `limped_pot`, `srp`, `3bp`, `4bp`, `allin_preflop`.
`max_raise_per_street = 1` initially. All-in available at low SPR.

| Pot | Flop | Turn | River |
|---|---|---|---|
| SRP | check, b33, b75 / vs bet: fold, call, raise(3x or jam) / vs raise: fold, call, jam | check, b50, b100 / same response sets | check, b75, b150, allin / vs bet: fold, call, raise-jam / vs raise: fold, call |
| 3BP | check, b25, b50 / vs bet: fold, call, raise-jam | check, b50, b100, allin / vs bet: fold, call, jam | check, b75, allin / vs bet: fold, call |
| 4BP | check, b25, allin / vs bet: fold, call, jam | check, allin / vs allin: fold, call | same as turn |
| limped | same shape as SRP (sizes from config) | | |

All sizes are config data (`TreeConfig`), not code, so they can be tuned
without touching solver logic. The exact percentages above ship as the
built-in default and as `configs/hu_100bb_limp.json`.

### All-in handling

If a player is all-in before the river, remaining board cards are dealt as
chance nodes directly to showdown; no further betting nodes are generated.

## 7. Tree and chance nodes (tree/)

- Node arena `Vec<Node>`; kinds: `Action { actor }`, `Chance(DealFlop |
  DealTurn | DealRiver)`, `Fold { winner }`, `Showdown`.
- Chance nodes do **not** materialize cards in the tree. During traversal the
  card set is enumerated (tiny tests) or sampled (public chance sampling)
  excluding dead cards (board so far; private cards are handled by range
  masking in the vector engine, by explicit deals in the scalar engine).
- Street flow: preflop → DealFlop(3) → flop betting → DealTurn → turn
  betting → DealRiver → river betting → showdown.
- Card-duplication invariants are tested explicitly (no board duplicates, no
  board∩hole overlap).

## 8. Information sets and storage

Info set key components: player to act, street, hand representation,
board representation, betting history (node id encodes history + pot type +
pot/stacks since the tree is fixed), all-in state.

- **Exact river / fixed-board solvers (Phases 2-4)**: hand = exact combo id
  (0..1326), board fixed → storage is flat `Vec<f64>` per (node, combo,
  action). Fast, no hashing.
- **Sampled/multistreet (Phases 4-6)**: storage keyed by (node id, board id
  or bucket id, hand index) in a hash map; hand may be an exact combo
  (Level 1) or a bucket (Level 2).

### Card abstraction levels (explicit)

- **Level 0**: exact combos, exact board — river and tiny tests only.
- **Level 1**: exact 1326 preflop combos, canonical flops (port of the
  1755-texture canonicalization), sampled turns/rivers.
- **Level 2**: per-street hand buckets (features: equity, hand strength,
  draw strength, nut potential, blockers, board texture, showdown value).
- Production path: Level 1/2 hybrid (Phase 6). Bucketing design details are
  deferred to the Phase 6 plan; the info-set key reserves space for it.

## 9. CFR engines (solver/)

Shared primitives:

- `regret_matching(regrets) -> strategy` (with + variant clipping)
- `CfrVariant`:
  - `Vanilla`
  - `CfrPlus { avg_delay: u32, linear_weighting: bool }` — regrets clipped at
    zero after update; average accumulation may start after `avg_delay`.
  - `Dcfr { alpha: f64, beta: f64, gamma: f64 }` — separate discounting of
    positive regrets, negative regrets, and strategy accumulation.
- Average strategy: always accumulated and exported; weighted by the
  **actor's own reach** (fixes audit issue #6); weighting per variant.

Engines:

- **Scalar engine** (`scalar.rs`): `trait Game { state, player, actions,
  next, is_terminal, payoff, infoset_key, chance_outcomes }` + recursive CFR
  with full traversal. Implementations: Kuhn, Leduc, tiny_river.
- **Vector engine** (`vector.rs`): per-combo `[f64]` traversal over the HU
  tree; reach = range vectors; showdown via strength-indexed evaluation with
  blocker handling (existing pattern, fixed payoffs).

Traversal modes (`sampling.rs`): full enumeration (tiny games), external
sampling (scalar engine), public chance sampling (vector engine, board cards
sampled per iteration). Deterministic seeds via an internal SplitMix64
(`rng.rs`, no external dependency).

## 10. Validation (validation/) — mandatory

- **Kuhn** (production scalar engine): game value → −1/18; Q never bets;
  P2 K always calls; exact best response; exploitability → 0.
- **Leduc** (production scalar engine): exploitability decreases
  monotonically (within tolerance) and reaches a threshold.
- **Poker sanity suite**: zero-sum payoffs, no duplicate cards, pot
  conservation, all-in conservation, fold/showdown payoff correctness,
  strategy sums to 1, chance probabilities sum to 1, no illegal actions.
- **Differential tests**: scalar vs vector on tiny river spots — same
  average strategy (tolerance) and same EV.

### Best response / exploitability

- Scalar games: exact BR by tree walk against the fixed average strategy.
- Fixed-board vector games (river, turn+river): **exact BR** — backward
  per-combo argmax against the opponent's reach-weighted distribution.
- Sampled games: BR estimate reported with seed and sample count.
- `exploitability = (BR₀ + BR₁) / 2` in **bb/hand**, always reported.
  Nothing is called "solved"/"GTO" without this number.

## 11. Outputs (reports/)

- **Tree stats**: info set count, terminal/chance node counts, actions per
  street, memory estimate.
- **Solver stats**: iterations, elapsed, average utility, exploitability,
  regret summary, strategy-change summary.
- **Strategy**: preflop combo strategy, postflop bucket strategy, exact
  river combo strategy, action frequency by street, EV by combo/bucket.
- Formats: CSV + JSON (HTML later). Output dir: `~/projects/_data/gto/hu/`.

## 12. CLI

Phase 2:

```
solve-hu-river --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000 \
               [--variant cfr+|dcfr] [--seed N] [--ranges uniform|file] [--out DIR]
```

Prints action-frequency table + exploitability (bb/hand); writes combo CSV /
JSON + stats. Later phases add `solve-hu-turn-river`, `solve-hu-flop`,
`solve-hu-preflop`, and `solve-hu-full --tree configs/hu_100bb_limp.json
--sampling public_chance`.

## 13. Implementation phases

1. **Fix foundation** (gto-core, surgical): failing test for SF-miss → fix
   `eval.rs`; failing test for phantom 2c → fix `showdown_values` (proper
   5/6/7-card evaluation); strict card-duplication tests; doc-mark
   `CfrSolver`/`solve()`/gto-py as river-only-correct approximation.
2. **River-only HU solver** (gto-hu): game/betting/terminal, river tree from
   config, scalar + vector engines with CFR+, Kuhn/Leduc/tiny_river, exact
   BR + exploitability, differential tests, `solve-hu-river` CLI.
3. **Turn+River**: river chance node, public chance sampling, sampled BR,
   all-in runout verification.
4. **Flop+Turn+River**: SRP/3BP trees, canonical flops, optional bucketing.
5. **Preflop tree**: limp lines, pot-type transitions, simplified postflop
   value model for debugging.
6. **Full HU abstract blueprint**: preflop ↔ postflop connection, DCFR,
   sampled boards, full strategy export, exploitability estimate.
7. **Performance**: profile → evaluator/showdown tables → parallel traversal
   → only then GPU.

Phases 1-2 are implemented first (this effort); each phase gets its own
implementation plan and is gated by its tests.

## 14. Hard prohibitions (restated)

No flop-call→showdown shortcut outside the river-only utility; no ignoring
turn/river chance nodes, blockers, or all-in runouts; no exporting latest
strategy as final; no convergence claims without exploitability (or at
minimum stability metrics, labeled as such); no GUI/GPU/6max/arbitrary bet
sizes/rake until the base is correct.

## 15. Acceptance criteria

1. Kuhn/Leduc CFR tests pass (production engine)
2. River HU exact solver passes payoff + exploitability tests
3. Turn+River handles chance nodes correctly
4. Flop+Turn+River never shortcuts to showdown
5. Preflop tree includes limp and open lines
6. Pot/stack accounting exact across all streets
7. Average strategy exported
8. Best response / exploitability implemented
9. Tree stats and solver stats exported
10. Documentation states: "This is an abstract HU NLHE equilibrium solver,
    not an unabstracted full GTO solver."

## 16. Risks / notes

- The vector engine's exact BR on the river is O(N²) over combos per
  terminal; acceptable initially (correctness first).
- Public-chance-sampled exploitability is an estimate; it is always labeled
  with seed and sample count to avoid overclaiming.
- `gto-core` fixes change numeric outputs of the existing library pipeline
  (it was evaluating phantom cards). The existing UI keeps working; numbers
  improve. Regenerating the 5265-spot Parquet library is **not** part of
  this effort (separate decision; ~40 min GPU).
