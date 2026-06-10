# Core Logic Review — 2026-06-10

Comprehensive review of solver core logic (bugs + inefficiencies), run as an
8-partition parallel review with per-finding adversarial verification
(2 independent refuters for critical/high findings, unanimous-confirm rule).

- Scope: `crates/gto-hu`, `crates/gto-core`, `crates/gto-cuda`, `crates/gto-py`,
  `src/gto/library`, `src/gto/api/routers`, `src/gto/solver/multistreet_gpu.py`.
  Excluded: toy validation games, trainer's hardcoded tables, review parser, web UI.
- Volume: 52 agents, 781 tool calls. 35 raw findings → **30 confirmed**,
  1 disputed (adjudicated below), 4 killed as false positives.
- All current test suites pass; these are issues the tests do not catch.

## Verdict summary

The exact-equilibrium core (**gto-hu**) is healthy: bucketing math, blueprint
measure (μ/zsum/Z-correction), showdown diff, betting/centi-bb accounting, tree
builders, and the evaluator were each adversarially probed and came back clean
except for the items below. The serious correctness bugs cluster in
**gto-cuda** (3) and the **Python boundary** (2).

## Bugs (confirmed)

### B1 — CRITICAL: FastCfrSolver ignores per-spot pots
`crates/gto-cuda/src/fast_cfr.rs:226` (root cause also `lib.rs:197-202`)

The tree is built once from spot 0 (`pot0 = half_pots[0] * 2`), and each
terminal's half-pot is broadcast across the batch
(`vec![half_pot; n]` → `g_hpot_nodes`). The genuine per-spot `g_hpot` buffer is
uploaded but never passed to any kernel. `multistreet_gpu.py` builds river jobs
with several distinct `pot_bb` per turn node and chunks them into mixed-pot
batches of 32 — so **every spot except spot 0 in each batch is solved with the
wrong pot**.

Fix: per-spot half-pot at terminals (scale `g_hpot_nodes` rows from
`half_pots`), or assert single-pot batches and group jobs by pot.

### B2 — CRITICAL: board-blocked opponent combos scored as guaranteed wins
`crates/gto-cuda/src/kernels.rs:37` (+ `cfr.rs:306,312`, `fast_cfr.rs:299`)

The showdown kernel skips opponent combos only on card-overlap with hero and
`ow == 0`. Board-blocked combos have strength 0 and range-weight 0, but the
default path passes **uniform 1.0 reach** (`batch_solve_rust` with no weights;
`FastCfrSolver` seeds `g_uniform` and never multiplies `ranges` in), so each
blocked opponent combo enters as `hs > 0 = os` → automatic hero win, inflating
EV and the normalizer (~11% of combos on a flop, ~18% on a river are phantom).
The CPU reference (`gto-core/src/cfr.rs:206-209`) filters these out. Live
callers: `solver.py:50`, `batch.py:195`, `multistreet_gpu.py:99`.

Fix: seed reach from `ranges` (0 for blocked combos) instead of uniform, or add
`if (os == 0) continue;` plus the symmetric hero guard in the kernel.

### B3 — HIGH: BatchCfrSolver showdown uses the ROOT pot, not the node pot
`crates/gto-cuda/src/cfr.rs:439` (parameter `_half_pot` at `cfr.rs:410`)

The call site computes the correct node half-pot
(`gpu_showdown(traverser, opp_reach, node.pot / 2.0)`) but the function ignores
it (`_half_pot`) and passes the static root array `self.g_hpot` to the kernel.
Every showdown reached after a bet/call is valued at the root pot. The CPU
reference threads the node pot correctly.

Fix: upload the node half-pot (broadcast per spot) or a per-node pot buffer as
FastCfrSolver's `g_hpot_nodes` does — then fix B1's broadcast there too.

> B1-B3 affect the production single-street paths: the 19,305-spot library was
> generated via `batch_solve_rust` (B2+B3 apply), and `batch_solve_fast`
> (B1+B2) serves multistreet GPU river jobs. After fixing, the library should
> be regenerated (~24 min on GPU) and `batch_solve_rust` / `batch_solve_fast`
> re-validated against `gto-core` CPU on shared inputs (differential protocol).

### B4 — HIGH: pyo3 bindings never release the GIL
`crates/gto-py/src/lib.rs` (all solve functions; e.g. turn-river solve ~349)

No `py.allow_threads` anywhere in the crate. `solve_hu_turn_river` holds the
GIL for the full ~30-40 s solve, so the HU router's
`ThreadPoolExecutor(max_workers=2)` cannot run two solves concurrently **and
the FastAPI event loop is frozen for the duration** (it cannot acquire the
GIL). Affects every binding: `solve_hu_river`, `solve_hu_turn_river`,
`solve_spot`, `solve_spot_multistreet`, `solve_flop_with_ev`, `equity`.

Fix: accept `py: Python` and wrap the heavy compute (solver.run + best-response
enumeration) in `py.allow_threads(|| ...)`. Directly relevant to Phase E1
(public deploy assumes the executor actually parallelizes).

### B5 — HIGH: multistreet chance EVs diluted by full card count
`crates/gto-core/src/multistreet.rs:305,331,344,355-356`

Turn/river child EVs are averaged with `/ n_turns` (=49) and `/ n_rivers`
(=48), but each live combo is only consistent with 47 turns / 46 rivers (its
2 hole cards block 2 candidates). The masked sum has 47 (46) nonzero terms
divided by 49 (48) → continuation EVs systematically scaled down ~4% per
street (compounding turn×river).

Fix: divide by the per-combo live count (accumulate a per-combo denominator),
not the raw candidate count.

### B6 — MEDIUM: equity() accepts overlapping hero/villain/board cards
`crates/gto-py/src/lib.rs:23` (+ `gto-core/src/equity.rs:21-45`)

Only arity is validated. `monte_carlo` dedups the *deck* but still evaluates
7-card hands that physically share a card — `GET /equity?hero=Ah Kh&villain=Ah Qd`
returns nonsense with HTTP 200. Same missing validation in `solve_spot` /
`solve_flop_with_ev` / `solve_spot_multistreet` (only the hu bindings check dupes).

Fix: reject when `set(hero+villain+board).len() != total` in all bindings.

### B7 — MEDIUM: sampled-mode lazy DCFR discount is not cumulative
`crates/gto-hu/src/solver/turn_river.rs:237-254`

Under `ChanceMode::Sample` a river (node,ctx) slice is touched on ~1/48 of
iterations, but each visit applies only the *current* iteration's
strategy/regret discount, not the cumulative product over skipped iterations —
early iterations are over-weighted in the average strategy vs enumerate mode.
Exploitability remains exact *for the strategy produced*; the strategy is just
more exploitable than properly-discounted DCFR would give. Largely vacuous for
the CFR+ default used by the web bindings; matters for DCFR sampled runs.

Fix: per-(node,ctx) `last_discount_iter` (as `scalar.rs` does) applying the
telescoped cumulative discount `((L+1)/(t+1))^gamma` on revisit — O(1).
Alternatively document the deviation.

### B8 — MEDIUM: gto-core average strategy ignores DCFR gamma weighting
`crates/gto-core/src/cfr.rs:182`

Strategy-sum accumulation is uniform across iterations while regrets use DCFR
discounting — inconsistent with the DCFR paper's gamma-weighted averaging.
gto-hu does this correctly; gto-core remains a single-spot approximation, but
the deviation slows its convergence.

### B9 — MEDIUM: no `cuCtxSetCurrent` on non-creating threads
`crates/gto-cuda/src/cuda_ffi.rs:138`

The CUDA context is only current on the thread that created it. Calls from
other threads (e.g. a ThreadPoolExecutor worker that didn't initialize the
solver) would fail. Currently mostly latent (solves run on the creating
thread), but a landmine for B4's fix and any executor-based GPU use.

### B10 — MEDIUM: multistreet_gpu blocked-combo masking loop is a no-op
`src/gto/solver/multistreet_gpu.py:196`

The aggregation loop that should zero board-blocked combo EVs doesn't actually
write anything — blocked combos keep phantom EVs in the aggregate (compounds B2).

### B11 — LATENT (adjudicated): CFR reach/opp_reach not swapped per traverser
`crates/gto-core/src/cfr.rs:99-103` (same shape in `multistreet.rs:60-63`)

Disputed in verification; adjudicated as **structurally real, currently
harmless**. `traverse(0, player, &r0, &r1, ...)` passes ranges[0]/ranges[1]
unswapped for both traversers, while the body assumes reach=traverser. Today
every gto-core caller passes two *identical* uniform ranges (verified:
`lib.rs:40`, `multistreet.rs:276/410/422`, `gto-py:125`), so the swap is a
no-op — but the first caller passing asymmetric ranges gets corrupted regrets
for player 1. One-line fix (bind `ranges[player]` / `ranges[1-player]`);
gto-hu `vector.rs:66-69` is the correct pattern.

### B12-B14 — LOW
- `crates/gto-hu/src/bin/solve_blueprint.rs:286` — CLI echoes raw `--weights`
  while the solver normalizes them (mislabels output metadata).
- `crates/gto-hu/src/tree/builder.rs:64` — open-bet sizing has no minimum-bet
  floor; tiny pots can emit sub-1bb/sub-min bets (legal-tree hygiene).
- `src/gto/library/batch.py:246` — `build_position_cache` silently drops caches
  for all but the first stack when given multiple stacks.

## Inefficiencies (confirmed; all on hot paths unless noted)

| # | Where | Issue | Est. win |
|---|---|---|---|
| I1 | `turn_river.rs:249`, `vector.rs:136` | `powf` recomputed per (combo,action) in the regret loop; only 2 values exist per iteration (sign of old regret). Precompute `d_pos`/`d_neg` per iteration. | Medium — thousands of `powf` per node/iter removed |
| I2 | `turn_river.rs:483-485`, `:397` | BR/eval recomputes+reallocates `average_strategy` O(na·N) per node (found independently by 3 reviewers). Hoist per node. | Medium — BR/exploitability passes |
| I3 | `gto-core/cfr.rs:211` | O(N²) showdown enumeration per iteration (vs gto-hu's O(N) two-sweep). | Medium (gto-core only) |
| I4 | `blueprint.rs:345` | No zero-reach early-exit before the dominant per-(leaf,m) subgame traversal. | Low-medium |
| I5 | `flop.rs:713` / `:685` | `stage_cards` materializes a 49-element Vec per chance visit (sample path discards all but one; turn_river.rs indexes directly). | Low |
| I6 | `flop.rs:531` | `showdown_payoffs`/`fold_payoffs` recomputed per (turn,river) ctx though constant per node. | Low |
| I7 | `blueprint.rs:240` | `z_weighted_compat` O(N²) recomputed each iteration per preflop fold terminal, with double allocation. | Low |
| I8 | `turn_river.rs:191` | `weighted_compat` recomputed at every fold terminal each traversal. | Low |
| I9 | `gto-core/cfr.rs:116,196` | Node (incl. children Vec) cloned per visit; `all_combos()` reallocated per showdown leaf. | Low |
| I10 | `fast_cfr.rs:302` | Per-iteration Vec clones of topo/children/desc in the CFR loop. | Low |
| I11 | `preflop.rs:255` | `aggregate_strategy` weights by full deal range, not reach-to-node (report-only skew). | Low |
| I12 | `range_builder.py:122` | Dead no-op loop on the /simulation request path. | Low |

## Recommended fix order

1. **B2 + B3 + B1** (gto-cuda correctness) → differential test vs gto-core CPU
   on mixed-pot, asymmetric-board batches → **regenerate the library** and
   compare drift vs current Parquet.
2. **B4** (GIL) + **B9** (context) — prerequisite for Phase E1's
   executor-based serving. Verify with two concurrent `/api/hu/river` calls.
3. **B5** (multistreet dilution) + **B10** (no-op masking) + **B11** (one-line
   reach fix) + **B6** (validation).
4. I1, I2 (cheap, measurable) — then the rest opportunistically.
5. B7 — decide: implement cumulative lazy discount or document the deviation.

## False positives killed in verification (for the record)

4 findings were refuted by adversarial verification (e.g. claims contradicted
by guards elsewhere or unreachable inputs); 1 finding was split and adjudicated
manually (B11). Full verifier transcripts: workflow run `wf_c805854e-55f`.
