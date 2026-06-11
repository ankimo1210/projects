# M1a — Custom Solve Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the M1a milestone of the mode-matrix spec: decommission the dead approximation-multistreet tier, add rake + general-sum exploitability to gto-hu's river and turn+river solvers, cut the PokerVariant thin seam, extend the pyo3 bindings with custom ranges / bet sizes / rake, and expose everything through a new `POST /api/solve` (GameSpec) endpoint + Custom Solve web form.

**Architecture:** All solver work happens in `gto-hu` (the equilibrium engine) and `gto-core` (shared types). Rake is applied in solver space at terminal evaluation — `game/terminal.rs` stays pure zero-sum and its asserts stay. Exploitability becomes general-sum-correct via per-player BR gains (NashConv), using the exact zero-sum identity when unraked so the rake=0 path is bit-identical. The API layer (FastAPI) translates GameSpec ⇄ binding calls; range notation parsing lives in Python (reusing `range_builder`).

**Tech Stack:** Rust (gto-core, gto-hu, gto-py/pyo3), Python 3.12 (FastAPI, pydantic, numpy), Next.js 16/React 19/Tailwind v4.

**Spec:** `gto/docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md` (rev 2). M1b (flop binding + job subsystem) is a SEPARATE plan — nothing here touches `FlopSolver` behavior.

**Environment facts the engineer must know:**
- Workspace venv lives at `~/projects/.venv`. Always `uv run --no-sync ...` (plain `uv run`/`uv sync` deletes the maturin-built `gto_py`/`gto_cuda` modules).
- Rebuild bindings after Rust changes: `cd ~/projects/gto && source ~/.cargo/env && uv run --no-sync maturin develop --uv --manifest-path crates/gto-py/Cargo.toml --release`
- Rust tests: `cargo test --manifest-path ~/projects/gto/Cargo.toml -p <crate>` (full-workspace run takes ~3h — run per-crate during development, full suite only in the final task).
- Python tests: `cd ~/projects && uv run --no-sync python -m pytest gto/tests -q`
- Card encoding: `card = rank*4 + suit`, rank 0=2…12=A, suits cdhs. Combo index `lo*(103-lo)/2 + hi-lo-1`, 1326 combos.
- Payoffs are centi-bb integers inside gto-hu (`BB = 100`); bb floats at boundaries.
- Player convention: p0 = SB/BTN = IP (acts last postflop), p1 = BB = OOP (acts first postflop, root actor of postflop trees).
- Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Stage exact paths, never `git add -A`. Never touch files outside `gto/` (other sessions work in this repo concurrently).

---

### Task 1: Decommission the approximation-multistreet tier

Adversarially verified: this tier is reachable from no API router and no web page. Deleting it breaks nothing live.

**Files:**
- Delete: `gto/crates/gto-core/src/multistreet.rs`
- Delete: `gto/src/gto/solver/multistreet_gpu.py`
- Delete: `gto/src/gto/library/batch_multistreet.py`
- Delete: `gto/src/gto/library/_sample_multistreet.py`
- Modify: `gto/crates/gto-core/src/lib.rs` (drop module + re-export)
- Modify: `gto/crates/gto-py/src/lib.rs` (drop two pyfunctions + import + registrations)
- Modify: `gto/tests/test_core_logic_fixes.py` (drop multistreet_gpu tests, keep range_builder tests)

- [ ] **Step 1: Confirm there are no callers outside the tier**

Run:
```bash
cd ~/projects/gto && grep -rn "solve_flop_with_ev\|solve_spot_multistreet\|multistreet_gpu\|batch_multistreet\|_sample_multistreet\|SubgameSolver\|solve_multistreet" src/ web/ crates/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.rs" | grep -v "crates/gto-core/src/multistreet.rs" | grep -v "src/gto/solver/multistreet_gpu.py" | grep -v "src/gto/library/batch_multistreet.py" | grep -v "src/gto/library/_sample_multistreet.py" | grep -v "tests/test_core_logic_fixes.py"
```
Expected remaining hits, ALL of which this task removes or which are comments:
`crates/gto-core/src/lib.rs:7` (`pub mod multistreet;`), `crates/gto-core/src/lib.rs:16` (re-export), `crates/gto-py/src/lib.rs:4` (import), `crates/gto-py/src/lib.rs` (the two pyfunctions + registrations at ~476-477), `crates/gto-cuda/src/lib.rs:91` (a comment — edit it in step 4). If anything ELSE appears, STOP and report.

- [ ] **Step 2: Delete the four files**

```bash
cd ~/projects/gto
git rm crates/gto-core/src/multistreet.rs src/gto/solver/multistreet_gpu.py src/gto/library/batch_multistreet.py src/gto/library/_sample_multistreet.py
```

- [ ] **Step 3: Remove the gto-core module + re-export**

In `gto/crates/gto-core/src/lib.rs` delete these two lines:
```rust
pub mod multistreet;
```
```rust
pub use multistreet::{SubgameSolver, MultiStreetResult, solve_multistreet};
```

- [ ] **Step 4: Remove the gto-py functions**

In `gto/crates/gto-py/src/lib.rs`:
- Line 4: change `use gto_core::{solve, all_combos, evaluate7, solve_multistreet};` to `use gto_core::{solve, all_combos, evaluate7};`
- Delete the whole `solve_flop_with_ev` pyfunction (lines ~140-194, from its doc comment through its closing brace).
- Delete the whole `solve_spot_multistreet` pyfunction (lines ~196-229).
- In the `#[pymodule]` block delete:
```rust
    m.add_function(wrap_pyfunction!(solve_spot_multistreet, m)?)?;
    m.add_function(wrap_pyfunction!(solve_flop_with_ev, m)?)?;
```
In `gto/crates/gto-cuda/src/lib.rs:91`, reword the stale comment `// spots that share both. Mixed-pot batches (the production multistreet path)` to `// spots that share both. Mixed-pot batches`.

- [ ] **Step 5: Prune the Python tests**

Rewrite `gto/tests/test_core_logic_fixes.py` to keep ONLY the range_builder (I12) tests. New full content:

```python
"""Regression tests for the 2026-06-10 core-logic review fixes (Python side).

B14 is covered in test_batch_position_cache.py. The B10 multistreet_gpu tests
were removed with the approximation-multistreet tier (M1a decommission,
docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md section 2).

Covers:
  I12 — range_builder dead no-op loop removed (behavior unchanged).
"""

from __future__ import annotations

from gto.library import range_builder


def test_compute_preflop_outcome_blocks_dead_cards():
    """Dead-card blockers still zero the matching combos after removing the
    dead no-op loop (the real blocker loop lives just below it)."""
    out_clean = range_builder.compute_preflop_outcome("BTN")
    out_blocked = range_builder.compute_preflop_outcome("BTN", dead_cards=["As", "Kd"])

    as_int = range_builder.card_int("A", "s")
    kd_int = range_builder.card_int("K", "d")

    ip = out_blocked["ip_weights"]
    oop = out_blocked["oop_call_weights"]
    for other in range(52):
        if other == as_int:
            continue
        idx = range_builder.combo_index(as_int, other)
        assert ip[idx] == 0.0 and oop[idx] == 0.0
    for other in range(52):
        if other == kd_int:
            continue
        idx = range_builder.combo_index(kd_int, other)
        assert ip[idx] == 0.0 and oop[idx] == 0.0

    # Blocking strictly removes weight, so it cannot exceed the unblocked sum.
    assert out_blocked["ip_weights"].sum() <= out_clean["ip_weights"].sum()


def test_no_dead_loop_in_source():
    """The dead no-op statement must be gone from compute_preflop_outcome."""
    import inspect

    src = inspect.getsource(range_builder.compute_preflop_outcome)
    assert "(idx * 2) // 1" not in src
```

- [ ] **Step 6: Build + test Rust, rebuild bindings, run pytest**

```bash
cd ~/projects/gto && source ~/.cargo/env
cargo build --manifest-path Cargo.toml -p gto-core -p gto-py        # expect: success
cargo test  --manifest-path Cargo.toml -p gto-core                  # expect: all pass (multistreet tests are gone with the file)
uv run --no-sync maturin develop --uv --manifest-path crates/gto-py/Cargo.toml --release
cd ~/projects && uv run --no-sync python -m pytest gto/tests -q      # expect: all pass
```
Note: the deleted `_data/gto/solutions_ms` Parquet directory is DATA, not code — leave it on disk untouched.

- [ ] **Step 7: Commit**

```bash
cd ~/projects
git add gto/crates/gto-core/src/lib.rs gto/crates/gto-py/src/lib.rs gto/crates/gto-cuda/src/lib.rs gto/tests/test_core_logic_fixes.py
git commit -m "refactor(gto): decommission the approximation-multistreet tier

Removes gto-core multistreet.rs (solve_multistreet, SubgameSolver), the
solve_spot_multistreet / solve_flop_with_ev pyfunctions, multistreet_gpu.py,
batch_multistreet.py and _sample_multistreet.py. Verified reachable from no
API router and no web page; superseded by gto-hu turn_river/flop (mode-matrix
spec rev 2, section 2). The solutions_ms Parquet data stays on disk.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(The deleted files are already staged by `git rm`.)

---

### Task 2: RakeModel type (gto-hu)

**Files:**
- Create: `gto/crates/gto-hu/src/game/rake.rs`
- Modify: `gto/crates/gto-hu/src/game/mod.rs`

- [ ] **Step 1: Write failing unit tests inside the new module**

Create `gto/crates/gto-hu/src/game/rake.rs`:

```rust
//! Rake model: chips removed from a won pot at terminal payout.
//! Amounts are centi-bb (`BB = 100`); rake is floored to the centi-bb grid
//! so payoffs stay integral. Applied in SOLVER space at terminal evaluation —
//! `terminal.rs` payoffs stay pure zero-sum (its asserts are untouched).

use super::street::Street;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RakeModel {
    /// Fraction of the pot taken (e.g. 0.05).
    pub pct: f64,
    /// Cap in centi-bb.
    pub cap_cbb: i64,
    /// No-flop-no-drop: pots won preflop are not raked.
    pub no_flop_no_drop: bool,
}

impl RakeModel {
    pub const NONE: RakeModel = RakeModel {
        pct: 0.0,
        cap_cbb: 0,
        no_flop_no_drop: true,
    };

    /// Online-site preset: 5% pot, 3bb cap, no flop no drop.
    pub fn site() -> Self {
        RakeModel { pct: 0.05, cap_cbb: 300, no_flop_no_drop: true }
    }

    /// Live preset: 10% pot, 5bb cap, dropped on every pot.
    pub fn live() -> Self {
        RakeModel { pct: 0.10, cap_cbb: 500, no_flop_no_drop: false }
    }

    pub fn is_none(&self) -> bool {
        self.pct == 0.0
    }

    /// Rake (centi-bb) taken from a pot won with the hand ending on `street`.
    pub fn rake_cbb(&self, pot: i64, street: Street) -> i64 {
        if self.pct == 0.0 {
            return 0;
        }
        if self.no_flop_no_drop && street == Street::Preflop {
            return 0;
        }
        ((pot as f64 * self.pct) as i64).min(self.cap_cbb)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn none_takes_nothing() {
        assert_eq!(RakeModel::NONE.rake_cbb(2000, Street::River), 0);
        assert!(RakeModel::NONE.is_none());
    }

    #[test]
    fn site_takes_5pct_capped_at_3bb() {
        let r = RakeModel::site();
        // 20bb pot -> 1bb rake (under the cap)
        assert_eq!(r.rake_cbb(2000, Street::River), 100);
        // 100bb pot -> 5bb uncapped, capped to 3bb
        assert_eq!(r.rake_cbb(10_000, Street::River), 300);
    }

    #[test]
    fn site_nfnd_skips_preflop_pots() {
        assert_eq!(RakeModel::site().rake_cbb(2000, Street::Preflop), 0);
        // live drops every pot
        assert_eq!(RakeModel::live().rake_cbb(2000, Street::Preflop), 200);
    }

    #[test]
    fn rake_floors_to_centibb() {
        // 5% of 1010 cbb = 50.5 -> floors to 50
        assert_eq!(RakeModel::site().rake_cbb(1010, Street::River), 50);
    }
}
```

- [ ] **Step 2: Export the module**

In `gto/crates/gto-hu/src/game/mod.rs` add (alongside existing `pub mod` lines and re-exports — read the file first and match its style):
```rust
pub mod rake;
```
and to its re-export block:
```rust
pub use rake::RakeModel;
```

- [ ] **Step 3: Run the tests**

Run: `cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu rake`
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu/src/game/rake.rs gto/crates/gto-hu/src/game/mod.rs
git commit -m "feat(gto-hu): RakeModel with none/site/live presets

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Rake + general-sum exploitability in VectorRiverSolver

The math (derivation, equal showdown contributions `c`, pot `P = 2c`, rake `r`):
winner nets `c − r`, loser nets `−c`, chop nets `(P−r)/2 − c = −r/2`. With
`diff = w_win − w_lose` and `W = w_win + w_lose + w_tie` (= `weighted_compat`):
`EV = c·diff − r·(w_win + w_tie/2) = win_bb·diff − r·(W + diff)/2`.
Fold pots: only the winner's payoff changes (`pot − r − contrib`).

Exploitability: `NashConv = Σ_p (BR_p − v_p)`. Unraked the game is exactly
zero-sum, so `NashConv = BR_0 + BR_1` (exact identity — keeps the rake=0
output bit-identical); raked we must use the per-player gains.

**Files:**
- Modify: `gto/crates/gto-hu/src/solver/vector.rs`
- Modify: `gto/crates/gto-hu/src/solver/turn_river.rs:733` (ExplReport construction — helper only)
- Modify: `gto/crates/gto-hu/src/solver/preflop.rs:420`, `blueprint.rs:788`, `flop.rs:1201` (same one-line helper switch)
- Test: `gto/crates/gto-hu/tests/test_rake_river.rs` (new)

- [ ] **Step 1: Extend ExplReport with a zero-sum helper (keeps 4 call sites one-line)**

In `gto/crates/gto-hu/src/solver/vector.rs` replace the `ExplReport` struct (lines 11-16) with:

```rust
/// Best-response report in bb/hand.
#[derive(Debug, Clone, Copy)]
pub struct ExplReport {
    pub br_value: [f64; 2],
    /// Avg-vs-avg game value per player ([0,0] where not computed —
    /// zero-sum callers via `zero_sum()`).
    pub game_value: [f64; 2],
    /// BR_p − game_value_p (general-sum per-player incentive to deviate).
    pub br_gain: [f64; 2],
    /// Σ_p br_gain_p. For the unraked (zero-sum) game computed as
    /// br0 + br1 — the identity is exact, and keeps rake=0 bit-identical.
    pub nashconv: f64,
    /// nashconv / 2 — bb/hand, 0 at equilibrium.
    pub exploitability: f64,
}

impl ExplReport {
    /// Report for an exactly zero-sum game: NashConv = br0 + br1.
    pub fn zero_sum(br_value: [f64; 2]) -> Self {
        let nashconv = br_value[0] + br_value[1];
        ExplReport {
            br_value,
            game_value: [0.0; 2],
            br_gain: br_value,
            nashconv,
            exploitability: nashconv / 2.0,
        }
    }
}
```

- [ ] **Step 2: Switch the four zero-sum constructors to the helper**

In each of `turn_river.rs` (~line 733), `preflop.rs` (~line 420), `blueprint.rs` (~line 788), `flop.rs` (~line 1201), the function ends with:
```rust
        ExplReport {
            br_value,
            exploitability: (br_value[0] + br_value[1]) / 2.0,
        }
```
Replace each with:
```rust
        ExplReport::zero_sum(br_value)
```
(turn_river.rs gets its full general-sum version in Task 4 — the helper keeps it compiling until then). Check imports: these files already import `ExplReport` via `use super::vector::ExplReport;` or the solver re-export — verify with `grep -n "ExplReport" <file>` and add `use super::vector::ExplReport;` if missing.

- [ ] **Step 3: Run the existing gto-hu suite to confirm the refactor is inert**

Run: `cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu --lib`
plus the fast integration tests:
`cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu --test test_river_solver --test test_tiny_river --test test_best_response`
Expected: all pass unchanged.

- [ ] **Step 4: Add the rake field and constructor to VectorRiverSolver**

In `vector.rs`:
- Add to imports: `use crate::game::rake::RakeModel;`
- Add field to the struct (after `variant: CfrVariant,`):
```rust
    /// Rake applied at terminals (RakeModel::NONE keeps the legacy
    /// zero-sum path bit-identical).
    rake: RakeModel,
```
- Replace `pub fn new(...)` so it delegates:
```rust
    pub fn new(tree: Tree, board: [u8; 5], ranges: [Range; 2], variant: CfrVariant) -> Self {
        Self::with_rake(tree, board, ranges, variant, RakeModel::NONE)
    }

    pub fn with_rake(
        tree: Tree,
        board: [u8; 5],
        mut ranges: [Range; 2],
        variant: CfrVariant,
        rake: RakeModel,
    ) -> Self {
        for r in &mut ranges {
            r.remove_blockers(&board);
        }
        // ... (move the entire existing `new` body here unchanged, and add
        //  `rake,` to the struct literal at the end)
    }
```

- [ ] **Step 5: Apply rake at the terminal arms — all three traversals**

The SAME two-arm change goes into `traverse`, `br_values`, and `avg_values` (their terminal arms are currently textually identical except for the player variable name: `traverser`, `br_player`, `player`). For each function, replace the two arms:

FoldTerminal arm (shown for `traverse`; use the function's own player variable):
```rust
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let mut pay = fold_payoffs(&state, winner)[traverser as usize] as f64 / 100.0;
                if traverser == winner {
                    // Rake comes out of the won pot; the loser's payoff is
                    // its own contribution either way.
                    pay -= self.rake.rake_cbb(state.pot(), state.street) as f64 / 100.0;
                }
                let compat = weighted_compat(&self.combos, opp_reach);
                compat.iter().map(|w| pay * w).collect()
            }
```

Showdown arm:
```rust
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(traverser))[traverser as usize] as f64 / 100.0;
                let diff = self.showdown_diff(opp_reach);
                let rake_bb = self.rake.rake_cbb(state.pot(), state.street) as f64 / 100.0;
                if rake_bb == 0.0 {
                    // Legacy zero-sum fast path — bit-identical when unraked.
                    diff.iter().map(|d| win_bb * d).collect()
                } else {
                    // winner nets win_bb − rake, loser −win_bb, chop −rake/2:
                    //   EV = win_bb·diff − rake·(compat + diff)/2
                    let compat = weighted_compat(&self.combos, opp_reach);
                    diff.iter()
                        .zip(compat.iter())
                        .map(|(d, w)| win_bb * d - rake_bb * (w + d) / 2.0)
                        .collect()
                }
            }
```

- [ ] **Step 6: Generalize game value + rework exploitability_bb**

Replace `game_value_p0` (keep it as a delegating wrapper) and `exploitability_bb`:

```rust
    /// Game value (bb/hand) to `player` when both follow the converged
    /// average strategy. Same normalization as `exploitability_bb`.
    pub fn game_value(&self, player: u8) -> f64 {
        let own = self.ranges[player as usize].weights;
        let opp = self.ranges[1 - player as usize].weights;
        let vals = self.avg_values(0, player, &opp);
        let compat = weighted_compat(&self.combos, &opp);
        let mut num = 0.0;
        let mut z = 0.0;
        for c in 0..N {
            if own[c] > 0.0 {
                num += own[c] * vals[c];
                z += own[c] * compat[c];
            }
        }
        if z > 0.0 { num / z } else { 0.0 }
    }

    pub fn game_value_p0(&self) -> f64 {
        self.game_value(0)
    }

    /// General-sum exploitability: per-player BR gain vs the avg-vs-avg
    /// game value; NashConv = Σ gains. Unraked, NashConv = br0 + br1
    /// exactly (zero-sum identity) — that branch is bit-identical to the
    /// pre-rake formula.
    pub fn exploitability_bb(&self) -> ExplReport {
        let mut br_value = [0.0f64; 2];
        #[allow(clippy::needless_range_loop)]
        for p in 0..2usize {
            let own = self.ranges[p].weights;
            let opp = self.ranges[1 - p].weights;
            let vals = self.br_values(0, p as u8, &opp);
            let compat = weighted_compat(&self.combos, &opp);
            let mut num = 0.0;
            let mut z = 0.0;
            for c in 0..N {
                if own[c] > 0.0 {
                    num += own[c] * vals[c];
                    z += own[c] * compat[c];
                }
            }
            br_value[p] = if z > 0.0 { num / z } else { 0.0 };
        }
        let game_value = [self.game_value(0), self.game_value(1)];
        let br_gain = [br_value[0] - game_value[0], br_value[1] - game_value[1]];
        let nashconv = if self.rake.is_none() {
            br_value[0] + br_value[1]
        } else {
            br_gain[0] + br_gain[1]
        };
        ExplReport {
            br_value,
            game_value,
            br_gain,
            nashconv,
            exploitability: nashconv / 2.0,
        }
    }
```

- [ ] **Step 7: Add root-level output helpers (consumed by Task 6's binding)**

Still in `vector.rs`:

```rust
    /// Range-vs-range equity for player 0 on this river (rake-independent:
    /// pure win probability, ties counted half).
    pub fn range_equity_p0(&self) -> f64 {
        let r0 = self.ranges[0].weights;
        let r1 = &self.ranges[1].weights;
        let diff = self.showdown.diff(&self.combos, r1);
        let compat = weighted_compat(&self.combos, r1);
        let mut num = 0.0;
        let mut z = 0.0;
        for c in 0..N {
            if r0[c] > 0.0 && compat[c] > 0.0 {
                // per-combo equity = (w_win + w_tie/2)/W = (W + diff)/(2W)
                num += r0[c] * (compat[c] + diff[c]) / 2.0;
                z += r0[c] * compat[c];
            }
        }
        if z > 0.0 { num / z } else { 0.5 }
    }

    /// Per-combo EV (bb) for `player` at the root under avg-vs-avg play,
    /// normalized per live opponent matchup. 0.0 where no live matchups.
    pub fn root_combo_evs(&self, player: u8) -> Vec<f64> {
        let opp = self.ranges[1 - player as usize].weights;
        let vals = self.avg_values(0, player, &opp);
        let compat = weighted_compat(&self.combos, &opp);
        (0..N)
            .map(|c| if compat[c] > 0.0 { vals[c] / compat[c] } else { 0.0 })
            .collect()
    }
```

- [ ] **Step 8: Write the hand-checkable integration tests**

Create `gto/crates/gto-hu/tests/test_rake_river.rs`:

```rust
//! Rake validation on degenerate river trees where equilibria are
//! hand-computable (mode-matrix spec section 4.2; replaces the spec's
//! "Kuhn+rake" idea — Kuhn runs on ScalarCfr, which has no rake).

use gto_hu::game::{RakeModel, BB};
use gto_hu::ranges::uniform_excluding;
use gto_hu::solver::{CfrVariant, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};

/// Check-only config: no bets exist, so every line is check/check ->
/// showdown and all values are direct showdown payoffs.
fn check_only() -> StreetConfig {
    StreetConfig {
        bet_pcts: vec![],
        allow_allin_bet: false,
        raise: gto_hu::tree::RaiseRule::None,
        max_raises: 0,
    }
}

fn solve(board: [u8; 5], cfg: &StreetConfig, rake: RakeModel, iters: u32) -> VectorRiverSolver {
    let tree = build_river_tree(20 * BB, 90 * BB, cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut s = VectorRiverSolver::with_rake(tree, board, ranges, CfrVariant::cfr_plus_default(), rake);
    s.run(iters);
    s
}

// Board card helper: rank 0=2..12=A, suit 0=c.. (card = rank*4+suit).
fn c(rank: u8, suit: u8) -> u8 { rank * 4 + suit }

#[test]
fn forced_checkdown_site_rake_values_are_exact() {
    // Mixed board, 20bb pot, site rake = min(5%*20bb, 3bb) = 1bb.
    // Forced checkdown: winner nets 10-1=9bb, loser -10bb, chop -0.5bb.
    // Aggregated over uniform vs uniform the totals must satisfy
    // gv0 + gv1 = -E[rake] with E[rake] = 1bb * P(non-chop) + 1bb * P(chop)
    // = exactly -1bb (every pot pays 1bb rake regardless of outcome).
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3), c(12, 0)];
    let s = solve(board, &check_only(), RakeModel::site(), 10);
    let gv = [s.game_value(0), s.game_value(1)];
    assert!((gv[0] + gv[1] + 1.0).abs() < 1e-9, "value sum {} != -1bb rake", gv[0] + gv[1]);
    // No decisions exist -> BR == avg value -> NashConv == 0.
    let e = s.exploitability_bb();
    assert!(e.nashconv.abs() < 1e-9, "nashconv {} != 0", e.nashconv);
    assert!(e.exploitability.abs() < 1e-9);
}

#[test]
fn forced_checkdown_board_plays_chop_tax_is_half_rake_each() {
    // Broadway board AKQJT rainbow: every combo plays the board straight ->
    // every showdown chops -> each player nets exactly -rake/2 = -0.5bb.
    let board = [c(12, 0), c(11, 1), c(10, 2), c(9, 3), c(8, 0)];
    let s = solve(board, &check_only(), RakeModel::site(), 10);
    assert!((s.game_value(0) + 0.5).abs() < 1e-9, "gv0 {}", s.game_value(0));
    assert!((s.game_value(1) + 0.5).abs() < 1e-9, "gv1 {}", s.game_value(1));
}

#[test]
fn unraked_report_matches_legacy_formula_exactly() {
    // rake=0 path: nashconv must equal br0+br1 EXACTLY (same arithmetic
    // as the pre-rake (br0+br1)/2 formula).
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3), c(12, 0)];
    let s = solve(board, &StreetConfig::srp_river(), RakeModel::NONE, 200);
    let e = s.exploitability_bb();
    assert_eq!(e.nashconv, e.br_value[0] + e.br_value[1]);
    assert_eq!(e.exploitability, (e.br_value[0] + e.br_value[1]) / 2.0);
}

#[test]
fn raked_equilibrium_differs_and_values_sum_negative() {
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3), c(12, 0)];
    let unraked = solve(board, &StreetConfig::srp_river(), RakeModel::NONE, 2000);
    let raked = solve(board, &StreetConfig::srp_river(), RakeModel::site(), 2000);
    // The raked game leaks value: total <= 0 strictly, bounded by the cap.
    let total = raked.game_value(0) + raked.game_value(1);
    assert!(total < 0.0, "raked total value {total} must be negative");
    assert!(total > -3.0, "cannot exceed the 3bb cap");
    // And the strategies must actually move at the root.
    let a = unraked.aggregate_strategy(0);
    let b = raked.aggregate_strategy(0);
    let max_diff = a.iter().zip(b.iter()).map(|((_, x), (_, y))| (x - y).abs()).fold(0.0, f64::max);
    assert!(max_diff > 0.005, "rake changed nothing at the root (max diff {max_diff})");
}
```
Note: `RaiseRule` must be exported from `gto_hu::tree` — check `crates/gto-hu/src/tree/mod.rs`; if `RaiseRule` is not re-exported, add it to the existing `pub use config::...` line.

- [ ] **Step 9: Run the new tests + the regression suite**

```bash
cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu --test test_rake_river
cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu --lib --test test_river_solver --test test_tiny_river --test test_best_response --test test_scalar_invariance
```
Expected: all pass. If `forced_checkdown_*` fails at tree build (check-only config rejected), inspect `build_river_tree`/`legal_actions` for an empty-bet-list assumption and report the finding before changing the builder.

- [ ] **Step 10: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu/src/solver/vector.rs gto/crates/gto-hu/src/solver/turn_river.rs gto/crates/gto-hu/src/solver/preflop.rs gto/crates/gto-hu/src/solver/blueprint.rs gto/crates/gto-hu/src/solver/flop.rs gto/crates/gto-hu/tests/test_rake_river.rs
git commit -m "feat(gto-hu): rake + general-sum exploitability in VectorRiverSolver

Rake applied in solver space at terminals (terminal.rs stays zero-sum,
asserts intact): fold pots dock the winner, showdowns use
EV = win_bb*diff - rake*(compat+diff)/2 (covers win/lose/chop). ExplReport
gains game_value/br_gain/nashconv; unraked NashConv uses the exact zero-sum
identity br0+br1, keeping the rake=0 path bit-identical. Hand-checked
degenerate-tree tests pin the forced-checkdown and all-chop values exactly.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Rake + outputs in TurnRiverSolver

Same shape as Task 3 — `turn_river.rs` has the same three traversals (`traverse` at ~line 247, `br_values` at ~538, `avg_values` nearby) with textually identical terminal arms, except Showdown uses `self.tables[ctx]` instead of `self.showdown`.

**Files:**
- Modify: `gto/crates/gto-hu/src/solver/turn_river.rs`
- Test: `gto/crates/gto-hu/tests/test_rake_turn_river.rs` (new)

- [ ] **Step 1: Add the rake field + with_rake constructor**

Mirror Task 3 step 4: import `crate::game::rake::RakeModel`, add `rake: RakeModel` field, `new(...)` delegates to `with_rake(..., RakeModel::NONE)`, struct literal gains `rake`.

- [ ] **Step 2: Apply rake at the terminal arms of all three traversals**

Exactly the Task 3 step 5 arms, with one substitution in the Showdown arm — the diff source is the river-context table:
```rust
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                let diff = table.diff(&self.combos, opp_reach);
```
then the same `rake_bb == 0.0` fast path / raked `compat` branch. The FoldTerminal arm is identical to Task 3's (turn-level folds have no ctx and that's fine — `weighted_compat` doesn't need one).

- [ ] **Step 3: Generalize game value + exploitability_bb**

Mirror Task 3 step 6, with the ctx argument threaded: `self.avg_values(0, player, &opp, None)` and `self.br_values(0, p as u8, &opp, None)`. Replace the `ExplReport::zero_sum(br_value)` interim from Task 3 step 2 with the full general-sum construction (same code as Task 3 step 6's tail).

- [ ] **Step 4: Add range_equity_p0 + root_combo_evs**

```rust
    /// Range-vs-range equity for player 0, river-enumerated via the
    /// per-context showdown tables (rake-independent).
    pub fn range_equity_p0(&self) -> f64 {
        let r0 = self.ranges[0].weights;
        let mut num = 0.0;
        let mut z = 0.0;
        for (ctx, &river) in self.rivers.iter().enumerate() {
            let mut o = self.ranges[1].weights;
            zero_card(&self.combos, river, &mut o);
            let diff = self.tables[ctx].diff(&self.combos, &o);
            let compat = weighted_compat(&self.combos, &o);
            for c in 0..N {
                if combo_blocks(self.combos[c], river) {
                    continue;
                }
                if r0[c] > 0.0 && compat[c] > 0.0 {
                    num += r0[c] * (compat[c] + diff[c]) / 2.0;
                    z += r0[c] * compat[c];
                }
            }
        }
        if z > 0.0 { num / z } else { 0.5 }
    }

    /// Per-combo EV (bb) for `player` at the turn root under avg-vs-avg
    /// play (chance enumerated), normalized per live opponent matchup.
    pub fn root_combo_evs(&self, player: u8) -> Vec<f64> {
        let opp = self.ranges[1 - player as usize].weights;
        let vals = self.avg_values(0, player, &opp, None);
        let compat = weighted_compat(&self.combos, &opp);
        (0..N)
            .map(|c| if compat[c] > 0.0 { vals[c] / compat[c] } else { 0.0 })
            .collect()
    }
```
(`zero_card` and `combo_blocks` already exist at the top of the file.)

- [ ] **Step 5: Tests**

Create `gto/crates/gto-hu/tests/test_rake_turn_river.rs`:

```rust
//! Rake on the turn+river solver: forced checkdown hand-check + the
//! unraked-identity regression. Mirrors test_rake_river.rs.

use gto_hu::game::{RakeModel, BB};
use gto_hu::ranges::uniform_excluding;
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn check_only() -> StreetConfig {
    StreetConfig { bet_pcts: vec![], allow_allin_bet: false, raise: RaiseRule::None, max_raises: 0 }
}

fn c(rank: u8, suit: u8) -> u8 { rank * 4 + suit }

fn solve(cfg: TurnTreeConfig, rake: RakeModel, iters: u32) -> TurnRiverSolver {
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3)];
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut s = TurnRiverSolver::with_rake(
        tree, board, ranges, CfrVariant::cfr_plus_default(), ChanceMode::Enumerate, rake,
    );
    s.run(iters);
    s
}

#[test]
fn forced_checkdown_site_rake_sums_to_minus_one_bb() {
    let cfg = TurnTreeConfig { turn: check_only(), river: check_only() };
    let s = solve(cfg, RakeModel::site(), 5);
    let total = s.game_value(0) + s.game_value(1);
    assert!((total + 1.0).abs() < 1e-9, "value sum {total} != -1bb rake");
    let e = s.exploitability_bb();
    assert!(e.nashconv.abs() < 1e-9);
}

#[test]
fn unraked_identity_holds() {
    let s = solve(TurnTreeConfig::srp(), RakeModel::NONE, 50);
    let e = s.exploitability_bb();
    assert_eq!(e.nashconv, e.br_value[0] + e.br_value[1]);
}
```
Note the constructor order: `with_rake(tree, board, ranges, variant, mode, rake)` — `mode` comes before `rake` to keep parameter order natural with `new`.

- [ ] **Step 6: Run + commit**

```bash
cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu --test test_rake_turn_river --test test_turn_chance --test test_scalar_invariance
cd ~/projects
git add gto/crates/gto-hu/src/solver/turn_river.rs gto/crates/gto-hu/tests/test_rake_turn_river.rs
git commit -m "feat(gto-hu): rake + general-sum exploitability in TurnRiverSolver

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(Skip the slow `test_turn_river_solver`/`test_turn_differential` here; the final task runs the full suite.)

---

### Task 5: PokerVariant thin seam (gto-core trait, gto-hu routing)

Thin seam ONLY (spec §4.3): behavioral lookups (combo count / combo→cards / blocker / strengths) go through the trait; the `[f64; N]` array layout and `const N` aliases stay. Named `PokerVariant` (NOT `Variant` — gto-hu's `CfrVariant` is the CFR-algorithm enum).

**Files:**
- Create: `gto/crates/gto-core/src/variant.rs`
- Modify: `gto/crates/gto-core/src/lib.rs`
- Modify: `gto/crates/gto-hu/src/ranges/mod.rs`
- Modify: `gto/crates/gto-hu/src/solver/showdown.rs` (add `from_strengths`)
- Modify: `gto/crates/gto-hu/src/solver/{vector.rs,turn_river.rs,flop.rs}` (route construction through the seam)
- Modify: `gto/docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md` (acceptance wording fix)

- [ ] **Step 1: Write the trait + NLHE impl with tests**

Create `gto/crates/gto-core/src/variant.rs`:

```rust
//! Game-variant seam: what a poker variant defines about hole cards.
//! NLHE is the only implementation (M1 thin seam). PLO arrives via the M4
//! experiment, which ALSO requires the runtime-length range refactor
//! ([f64; NUM_COMBOS] arrays) and k-card blocker inclusion-exclusion —
//! deliberately out of scope here (mode-matrix spec section 4.3).

use crate::eval::showdown_strengths;
use crate::range::{all_combos, NUM_COMBOS};

pub trait PokerVariant {
    type HoleCards: Copy;
    fn combo_count(&self) -> usize;
    fn combo_cards(&self, i: usize) -> Self::HoleCards;
    /// 52-bit card-occupancy mask for blocker tests.
    fn blocker_mask(&self, h: &Self::HoleCards) -> u64;
    /// Strength of every combo on `board` (0 = blocked / invalid).
    fn showdown_strengths(&self, board: &[u8]) -> Vec<u16>;
}

pub struct Nlhe {
    combos: Vec<(u8, u8)>,
}

impl Nlhe {
    pub fn new() -> Self {
        Nlhe { combos: all_combos() }
    }

    /// Combo list in index order (the canonical NLHE (lo, hi) pairs).
    pub fn combos(&self) -> &[(u8, u8)] {
        &self.combos
    }
}

impl Default for Nlhe {
    fn default() -> Self {
        Self::new()
    }
}

impl PokerVariant for Nlhe {
    type HoleCards = (u8, u8);

    fn combo_count(&self) -> usize {
        NUM_COMBOS
    }

    fn combo_cards(&self, i: usize) -> (u8, u8) {
        self.combos[i]
    }

    fn blocker_mask(&self, h: &(u8, u8)) -> u64 {
        (1u64 << h.0) | (1u64 << h.1)
    }

    fn showdown_strengths(&self, board: &[u8]) -> Vec<u16> {
        showdown_strengths(board)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::range::combo_index;

    #[test]
    fn count_and_roundtrip() {
        let v = Nlhe::new();
        assert_eq!(v.combo_count(), 1326);
        for i in 0..v.combo_count() {
            let (a, b) = v.combo_cards(i);
            assert!(a < b);
            assert_eq!(combo_index(a, b), i);
        }
    }

    #[test]
    fn blocker_mask_has_exactly_two_bits() {
        let v = Nlhe::new();
        let m = v.blocker_mask(&(0, 51));
        assert_eq!(m.count_ones(), 2);
        assert_ne!(m & 1, 0);
        assert_ne!(m & (1 << 51), 0);
    }

    #[test]
    fn strengths_delegate_to_eval() {
        let v = Nlhe::new();
        let board = [0u8, 5, 10, 15, 20];
        assert_eq!(v.showdown_strengths(&board), showdown_strengths(&board));
    }
}
```
Check `eval::showdown_strengths`'s parameter type first (`grep -n "pub fn showdown_strengths" crates/gto-core/src/eval.rs` — it is `&[Card]`; `Card` is `u8`-backed: check `card.rs` for whether `Card` is a newtype. If `Card(pub u8)`, adapt the delegation: `showdown_strengths(&board.iter().map(|&c| Card(c)).collect::<Vec<_>>())` — match the existing call in `gto-hu/src/solver/showdown.rs:18`, which compiles today; copy its convention exactly).

In `gto/crates/gto-core/src/lib.rs` add:
```rust
pub mod variant;
```
and to the re-exports:
```rust
pub use variant::{Nlhe, PokerVariant};
```

Run: `cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-core variant` — expected: 3 passed.

- [ ] **Step 2: Expose the shared NLHE instance in gto-hu**

In `gto/crates/gto-hu/src/ranges/mod.rs`:

```rust
//! Range handling. The 1326-combo representation comes from gto-core.

pub use gto_core::range::{all_combos, combo_index, Range, NUM_COMBOS};
pub use gto_core::variant::{Nlhe, PokerVariant};

use std::sync::OnceLock;

/// The shared NLHE variant instance. M1 thin seam: solvers obtain combo
/// lists / strengths / blocker masks through this rather than calling
/// gto-core free functions directly.
pub fn nlhe() -> &'static Nlhe {
    static NLHE: OnceLock<Nlhe> = OnceLock::new();
    NLHE.get_or_init(Nlhe::new)
}

/// Uniform range with board blockers removed.
pub fn uniform_excluding(board: &[u8]) -> Range {
    let mut r = Range::new_uniform();
    r.remove_blockers(board);
    r
}
```

- [ ] **Step 3: Route ShowdownTable construction through the variant**

In `gto/crates/gto-hu/src/solver/showdown.rs`, split `new`:

```rust
    pub fn new(board: &[u8; 5]) -> Self {
        Self::from_strengths(crate::ranges::nlhe().showdown_strengths(board))
    }

    /// Build from variant-provided strengths (PokerVariant seam).
    pub fn from_strengths(strengths: Vec<u16>) -> Self {
        let mut sorted_idx: Vec<usize> = (0..N).filter(|&i| strengths[i] > 0).collect();
        sorted_idx.sort_unstable_by_key(|&i| strengths[i]);
        ShowdownTable { strengths, sorted_idx }
    }
```
(Adjust the existing direct `showdown_strengths(board)` call/import accordingly; if the existing call adapts `&[u8;5]` to `&[Card]`, move that adaptation into `Nlhe::showdown_strengths` as discovered in step 1.)

- [ ] **Step 4: Route the solvers' combo lists + blocker checks through the seam**

In `vector.rs`, `turn_river.rs`, `flop.rs`: replace each `combos: all_combos()` (in constructors) with `combos: crate::ranges::nlhe().combos().to_vec()`, and in `turn_river.rs` replace the body of `combo_blocks`:
```rust
#[inline]
fn combo_blocks(combo: (u8, u8), card: u8) -> bool {
    use crate::ranges::{nlhe, PokerVariant};
    nlhe().blocker_mask(&combo) & (1u64 << card) != 0
}
```
Then verify no behavioral gto-core lookups bypass the seam in the three vector solvers:
```bash
grep -n "all_combos()\|showdown_strengths(" crates/gto-hu/src/solver/vector.rs crates/gto-hu/src/solver/turn_river.rs crates/gto-hu/src/solver/flop.rs
```
Expected: zero hits (uses go through `nlhe()` / `ShowdownTable::new`). `NUM_COMBOS` as `const N` array dimension REMAINS — that is the documented thin-seam boundary.

- [ ] **Step 5: Bit-identity check + spec amendment + commit**

```bash
cargo test --manifest-path ~/projects/gto/Cargo.toml -p gto-hu --lib --test test_river_solver --test test_tiny_river --test test_rake_river --test test_rake_turn_river --test test_scalar_invariance --test test_betting --test test_regret
```
Expected: all pass (the seam is pure routing — identical values).

In the spec (`docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md` §4.3), replace acceptance criterion (b):
> (b) no direct `NUM_COMBOS` reference outside `gto-core::range` + the NLHE variant impl;

with:
> (b) no *behavioral* use of gto-core combo/strength/blocker functions outside
> the trait path in the three vector solvers; `NUM_COMBOS` may remain only as
> the `const N` array-dimension alias (the thin-seam boundary — array-type
> genericity is M4 scope);

```bash
cd ~/projects
git add gto/crates/gto-core/src/variant.rs gto/crates/gto-core/src/lib.rs gto/crates/gto-hu/src/ranges/mod.rs gto/crates/gto-hu/src/solver/showdown.rs gto/crates/gto-hu/src/solver/vector.rs gto/crates/gto-hu/src/solver/turn_river.rs gto/crates/gto-hu/src/solver/flop.rs gto/docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md
git commit -m "feat(gto-core): PokerVariant trait + NLHE impl; thin-seam routing in gto-hu

Behavioral combo/strength/blocker lookups in the three vector solvers now go
through the PokerVariant trait (shared Nlhe instance). [f64; N] layouts stay —
the documented thin-seam boundary; array genericity is M4 PLO scope. Spec
acceptance 4.3(b) reworded to match. Bit-identical on the existing suite.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: gto-py — extend solve_hu_river (ranges / bet sizes / rake / new outputs)

Also fixes a latent bug this feature would expose: the combo export filters by `solver.ranges[0]` (SB), but the root actor is BB (p1) — wrong filter once ranges differ.

**Files:**
- Modify: `gto/crates/gto-py/src/lib.rs`
- Test: `gto/tests/test_hu_custom_solve.py` (new)

- [ ] **Step 1: Add shared helpers (used by both bindings)**

In `gto/crates/gto-py/src/lib.rs` (above the pyfunctions):

```rust
/// Build a Range from optional API weights; falls back to uniform.
/// Validation: length == 1326, all finite and >= 0, positive sum.
fn range_from_weights(
    weights: Option<Vec<f64>>,
    board: &[u8],
) -> PyResult<gto_hu::ranges::Range> {
    use gto_hu::ranges::{uniform_excluding, Range, NUM_COMBOS};
    match weights {
        None => Ok(uniform_excluding(board)),
        Some(w) => {
            if w.len() != NUM_COMBOS {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "range weights must have length {NUM_COMBOS}, got {}",
                    w.len()
                )));
            }
            if w.iter().any(|x| !x.is_finite() || *x < 0.0) {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "range weights must be finite and non-negative",
                ));
            }
            let mut r = Range::new_empty();
            r.weights.copy_from_slice(&w);
            r.remove_blockers(board);
            if r.total_weight() <= 0.0 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "range has no live combos on this board",
                ));
            }
            Ok(r)
        }
    }
}

/// StreetConfig for the river from pot_type + overrides.
fn river_config(
    pot_type: Option<&str>,
    bet_pcts: Option<Vec<u32>>,
    max_raises: Option<u8>,
) -> PyResult<gto_hu::tree::StreetConfig> {
    use gto_hu::tree::StreetConfig;
    let mut cfg = match pot_type.unwrap_or("srp") {
        "srp" => StreetConfig::srp_river(),
        "3bet" => StreetConfig::threebet_river(),
        "4bet" => StreetConfig::fourbet_street(),
        other => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unknown pot_type '{other}' (srp | 3bet | 4bet)"
            )))
        }
    };
    if let Some(p) = bet_pcts {
        if p.iter().any(|&x| x == 0) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "bet_pcts must be positive",
            ));
        }
        cfg.bet_pcts = p;
    }
    if let Some(m) = max_raises {
        cfg.max_raises = m;
    }
    Ok(cfg)
}

/// RakeModel from optional pct/cap (bb). None/0.0 -> RakeModel::NONE.
fn rake_from_args(rake_pct: Option<f64>, rake_cap_bb: Option<f64>) -> PyResult<gto_hu::game::RakeModel> {
    use gto_hu::game::RakeModel;
    let pct = rake_pct.unwrap_or(0.0);
    if !(0.0..0.5).contains(&pct) {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "rake_pct must be in [0, 0.5)",
        ));
    }
    if pct == 0.0 {
        return Ok(RakeModel::NONE);
    }
    let cap_bb = rake_cap_bb.unwrap_or(f64::MAX / 200.0);
    if cap_bb <= 0.0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "rake_cap_bb must be positive",
        ));
    }
    Ok(RakeModel { pct, cap_cbb: (cap_bb * 100.0) as i64, no_flop_no_drop: true })
}
```

- [ ] **Step 2: Extend the solve_hu_river signature and body**

Change the signature to:
```rust
#[pyfunction]
#[pyo3(signature = (board, pot_bb, effective_stack_bb, iterations=None, ip_weights=None, oop_weights=None, bet_pcts=None, max_raises=None, pot_type=None, rake_pct=None, rake_cap_bb=None))]
fn solve_hu_river(
    py: Python<'_>,
    board: Vec<String>,
    pot_bb: f64,
    effective_stack_bb: f64,
    iterations: Option<u32>,
    ip_weights: Option<Vec<f64>>,
    oop_weights: Option<Vec<f64>>,
    bet_pcts: Option<Vec<u32>>,
    max_raises: Option<u8>,
    pot_type: Option<&str>,
    rake_pct: Option<f64>,
    rake_cap_bb: Option<f64>,
) -> PyResult<PyObject> {
```
Inside, BEFORE `py.allow_threads`, resolve everything fallible:
```rust
    let cfg = river_config(pot_type, bet_pcts, max_raises)?;
    let rake = rake_from_args(rake_pct, rake_cap_bb)?;
    let ranges = [
        range_from_weights(ip_weights, &board5)?,   // p0 = SB/IP
        range_from_weights(oop_weights, &board5)?,  // p1 = BB/OOP
    ];
```
and replace the closure's tree/ranges/solver construction with:
```rust
        let tree = build_river_tree(pot, stack, &cfg);
        let mut solver =
            VectorRiverSolver::with_rake(tree, board5, ranges, CfrVariant::cfr_plus_default(), rake);
```
Extend `HuSolveOutput` (the shared struct at the top of the file):
```rust
struct HuSolveOutput {
    root: Vec<(String, f64)>,
    expl: gto_hu::solver::ExplReport,
    game_value: f64,
    elapsed: f64,
    /// (card_a, card_b, per-action freqs, ev_bb) for each in-range combo
    /// of the ROOT ACTOR (BB/OOP — p1).
    combo_data: Vec<(u8, u8, Vec<f64>, f64)>,
    equity_sb: f64,
}
```
In the closure, after `let root = ...`, replace the combo loop (fixing the latent ranges[0] filter bug — the root actor is BB = p1):
```rust
        let combo_evs = solver.root_combo_evs(1);
        let equity_sb = solver.range_equity_p0();
        let mut combo_data = Vec::new();
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            // Root node actor is BB (p1) — filter by ITS range, not SB's.
            if solver.ranges[1].weights[c] == 0.0 {
                continue;
            }
            let s = solver.average_strategy(0, c);
            combo_data.push((ca, cb, s.iter().take(na).copied().collect::<Vec<f64>>(), combo_evs[c]));
        }
```
After the closure, extend the dict (keep every existing key — backward compatible):
```rust
    dict.set_item("br_gain_sb", expl.br_gain[0])?;
    dict.set_item("br_gain_bb", expl.br_gain[1])?;
    dict.set_item("nashconv", expl.nashconv)?;
    dict.set_item("game_value_bb", expl.game_value[1])?;
    dict.set_item("equity_sb", out.equity_sb)?;
    dict.set_item("equity_bb", 1.0 - out.equity_sb)?;
```
and in the combo-list loop add `e.set_item("ev", *ev)?;` (the 4th tuple element).
NOTE: `game_value_sb` currently comes from `solver.game_value_p0()`; keep it, and note `expl.game_value[0]` equals it — use `expl.game_value[0]` to avoid the extra traversal: replace `let game_value = solver.game_value_p0();` with `let game_value = expl.game_value[0];` (the ExplReport now computes both).

- [ ] **Step 3: Apply the same dict/combo changes to solve_hu_turn_river's OUTPUT only**

`solve_hu_turn_river` gets its full input extension in Task 7, but it shares `HuSolveOutput` — so its closure must compile now: extend its `combo_data.push((ca, cb, ...))` with `solver.root_combo_evs(1)[c]` as the 4th element, set `equity_sb: solver.range_equity_p0()`, replace `solver.game_value_p0()` with the ExplReport's `game_value[0]`, and add the same six new dict keys + the `ev` combo field. (Its export filter `solver.export_weight(1, None, c)` already filters by p1 — correct; leave it.)

- [ ] **Step 4: Build, rebuild the extension, write the Python tests**

```bash
cd ~/projects/gto && source ~/.cargo/env
cargo build --manifest-path Cargo.toml -p gto-py
uv run --no-sync maturin develop --uv --manifest-path crates/gto-py/Cargo.toml --release
```

Create `gto/tests/test_hu_custom_solve.py`:

```python
"""M1a: custom ranges / bet sizes / rake on the gto_py HU bindings."""

import pytest

try:
    import gto_py

    HAS = hasattr(gto_py, "solve_hu_river")
except ImportError:
    HAS = False

pytestmark = pytest.mark.skipif(not HAS, reason="gto_py not built in this venv")

BOARD5 = ["Ah", "Kd", "7s", "2c", "9h"]
NUM_COMBOS = 1326


def _combo_index(a: int, b: int) -> int:
    lo, hi = (a, b) if a < b else (b, a)
    return lo * (103 - lo) // 2 + hi - lo - 1


def _card(s: str) -> int:
    return "23456789TJQKA".index(s[0]) * 4 + "cdhs".index(s[1])


def test_baseline_signature_still_works():
    r = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 300)
    assert {"strategy", "exploitability", "br_sb", "br_bb", "combos"} <= set(r)
    # new outputs present
    assert {"nashconv", "br_gain_sb", "br_gain_bb", "equity_sb", "equity_bb", "game_value_bb"} <= set(r)
    assert r["equity_sb"] + r["equity_bb"] == pytest.approx(1.0)
    # unraked: nashconv == br_sb + br_bb exactly
    assert r["nashconv"] == r["br_sb"] + r["br_bb"]
    assert all("ev" in c for c in r["combos"])


def test_custom_oop_range_filters_combo_export():
    # OOP holds only QQ (6 combos, none blocked by this board).
    w = [0.0] * NUM_COMBOS
    qq = []
    q_cards = [_card("Q" + s) for s in "cdhs"]
    for i, a in enumerate(q_cards):
        for b in q_cards[i + 1:]:
            qq.append(_combo_index(a, b))
    for i in qq:
        w[i] = 1.0
    r = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 300, None, w)
    # Combo export is the ROOT ACTOR's (OOP) range -> exactly the QQ combos.
    got = {(c["card_a"], c["card_b"]) for c in r["combos"]}
    assert len(got) == 6
    assert all(a[0] == "Q" and b[0] == "Q" for a, b in got)


def test_invalid_ranges_rejected():
    with pytest.raises(ValueError):
        gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 100, [1.0] * 10, None)
    blocked = [0.0] * NUM_COMBOS
    blocked[_combo_index(_card("Ah"), _card("Kd"))] = 1.0  # both on board
    with pytest.raises(ValueError):
        gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 100, blocked, None)


def test_custom_bet_sizes_change_action_set():
    base = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 200)
    custom = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 200, None, None, [50], 0)
    assert base["actions"] != custom["actions"]
    assert any("50" in a for a in custom["actions"])


def test_rake_reduces_total_value():
    raked = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 500, None, None, None, None, None, 0.05, 3.0)
    total = raked["game_value_sb"] + raked["game_value_bb"]
    assert total < 0.0
    # raked nashconv uses per-player gains, still ~0 at convergence
    assert raked["nashconv"] == pytest.approx(
        raked["br_gain_sb"] + raked["br_gain_bb"]
    )


def test_bad_rake_rejected():
    with pytest.raises(ValueError):
        gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 100, None, None, None, None, None, 0.9)
```

Run: `cd ~/projects && uv run --no-sync python -m pytest gto/tests/test_hu_custom_solve.py -v`
Expected: 6 passed.

- [ ] **Step 5: Full pytest + commit**

```bash
cd ~/projects && uv run --no-sync python -m pytest gto/tests -q   # all pass
git add gto/crates/gto-py/src/lib.rs gto/tests/test_hu_custom_solve.py
git commit -m "feat(gto-py): custom ranges, bet sizes, pot type and rake on solve_hu_river

Adds ip_weights/oop_weights (1326 floats), bet_pcts/max_raises/pot_type
(StreetConfig), rake_pct/rake_cap_bb (RakeModel). New outputs: nashconv,
br_gain_sb/bb, game_value_bb, equity_sb/bb, per-combo ev. Fixes a latent
export bug: combo strategies are the ROOT ACTOR's (BB/OOP) — the filter used
ranges[0] (SB), harmless for uniform ranges but wrong for custom ones.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: gto-py — extend solve_hu_turn_river inputs

**Files:**
- Modify: `gto/crates/gto-py/src/lib.rs`
- Test: extend `gto/tests/test_hu_custom_solve.py`

- [ ] **Step 1: Extend the signature**

```rust
#[pyo3(signature = (board, pot_bb, effective_stack_bb, iterations=None, seed=None, ip_weights=None, oop_weights=None, turn_bet_pcts=None, river_bet_pcts=None, max_raises=None, pot_type=None, rake_pct=None, rake_cap_bb=None))]
```
Resolve before `allow_threads` (mirror Task 6 step 2):
```rust
    let mut cfg = match pot_type.unwrap_or("srp") {
        "srp" => TurnTreeConfig::srp(),
        "3bet" => TurnTreeConfig {
            turn: gto_hu::tree::StreetConfig::threebet_turn(),
            river: gto_hu::tree::StreetConfig::threebet_river(),
        },
        "4bet" => TurnTreeConfig {
            turn: gto_hu::tree::StreetConfig::fourbet_street(),
            river: gto_hu::tree::StreetConfig::fourbet_street(),
        },
        other => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unknown pot_type '{other}' (srp | 3bet | 4bet)"
            )))
        }
    };
    if let Some(p) = turn_bet_pcts {
        if p.iter().any(|&x| x == 0) {
            return Err(pyo3::exceptions::PyValueError::new_err("turn_bet_pcts must be positive"));
        }
        cfg.turn.bet_pcts = p;
    }
    if let Some(p) = river_bet_pcts {
        if p.iter().any(|&x| x == 0) {
            return Err(pyo3::exceptions::PyValueError::new_err("river_bet_pcts must be positive"));
        }
        cfg.river.bet_pcts = p;
    }
    if let Some(m) = max_raises {
        cfg.turn.max_raises = m;
        cfg.river.max_raises = m;
    }
    let rake = rake_from_args(rake_pct, rake_cap_bb)?;
    let ranges = [
        range_from_weights(ip_weights, &board4)?,
        range_from_weights(oop_weights, &board4)?,
    ];
```
and construct with `TurnRiverSolver::with_rake(tree, board4, ranges, CfrVariant::cfr_plus_default(), mode, rake)` where `let tree = build_turn_river_tree(pot, stack, &cfg);`.

- [ ] **Step 2: Rebuild + extend tests**

Rebuild (same maturin command). Append to `gto/tests/test_hu_custom_solve.py`:

```python
BOARD4 = ["Ah", "Kd", "7s", "2c"]


def test_turn_river_custom_range_and_rake():
    w = [0.0] * NUM_COMBOS
    # OOP holds only 88 (none blocked)
    e_cards = [_card("8" + s) for s in "cdhs"]
    for i, a in enumerate(e_cards):
        for b in e_cards[i + 1:]:
            w[_combo_index(a, b)] = 1.0
    r = gto_py.solve_hu_turn_river(
        BOARD4, 20.0, 90.0, 400, 42, None, w, None, None, None, None, 0.05, 3.0
    )
    got = {(c["card_a"], c["card_b"]) for c in r["combos"]}
    assert len(got) == 6 and all(a[0] == "8" and b[0] == "8" for a, b in got)
    assert r["game_value_sb"] + r["game_value_bb"] < 0.0  # rake leaks value
    assert "ev" in r["combos"][0]


def test_turn_river_baseline_unchanged():
    r = gto_py.solve_hu_turn_river(BOARD4, 20.0, 90.0, 300)
    assert r["nashconv"] == r["br_sb"] + r["br_bb"]
```

Run: `uv run --no-sync python -m pytest gto/tests/test_hu_custom_solve.py -v` — expected: 8 passed.

- [ ] **Step 3: Commit**

```bash
cd ~/projects
git add gto/crates/gto-py/src/lib.rs gto/tests/test_hu_custom_solve.py
git commit -m "feat(gto-py): custom ranges, per-street bet sizes, pot type and rake on solve_hu_turn_river

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Range notation parser (Python)

**Files:**
- Create: `gto/src/gto/library/range_notation.py`
- Test: `gto/tests/test_range_notation.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `gto/tests/test_range_notation.py`:

```python
"""Range-notation grammar: "AA,AKs:0.5,KQo" -> weight vector [1326]."""

import numpy as np
import pytest
from gto.library import range_builder
from gto.library.range_notation import parse_range_notation


def test_single_pair_class():
    w = parse_range_notation("AA")
    assert w.shape == (1326,)
    assert w.sum() == pytest.approx(6.0)  # 6 AA combos at weight 1
    for idx in range_builder.hand_to_combo_indices("AA"):
        assert w[idx] == 1.0


def test_weighted_and_multiple_classes():
    w = parse_range_notation("AA, AKs:0.5, KQo")
    assert w[range_builder.hand_to_combo_indices("AKs")[0]] == 0.5
    assert w[range_builder.hand_to_combo_indices("KQo")[0]] == 1.0
    assert w.sum() == pytest.approx(6 * 1.0 + 4 * 0.5 + 12 * 1.0)


def test_last_assignment_wins_and_bounds():
    w = parse_range_notation("AKs:0.2,AKs:0.9")
    assert w[range_builder.hand_to_combo_indices("AKs")[0]] == 0.9


@pytest.mark.parametrize("bad", ["", "ZZ", "AKs:1.5", "AKs:-1", "AKs:abc", "AK"])
def test_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_range_notation(bad)
```
Note: confirm `range_builder.hand_to_combo_indices("AK")` behavior first — the existing function treats a 2-char non-pair as offsuit+suited? Read `range_builder.py:51-66`: `"AK"` (len 2, r1 != r2) falls to the offsuit branch (12 combos, NOT 16). Decide: the notation grammar REQUIRES the s/o suffix for non-pairs (reject bare "AK") — that is what the test encodes.

Run: `uv run --no-sync python -m pytest gto/tests/test_range_notation.py -v` — expected: FAIL (module missing).

- [ ] **Step 2: Implement**

Create `gto/src/gto/library/range_notation.py`:

```python
"""Range-notation parser: "AA,AKs:0.5,KQo" -> np.ndarray[1326] of weights.

Grammar (comma-separated entries, whitespace ignored):
  entry  = class [":" weight]
  class  = RR (pair) | RRs (suited) | RRo (offsuit), ranks from AKQJT98765432
  weight = float in [0, 1]; default 1.0; later entries overwrite earlier ones.

Bare two-rank classes without s/o ("AK") are rejected — explicit is better
than a silent 12-combo offsuit interpretation.
"""

from __future__ import annotations

import numpy as np

from gto.library.range_builder import NUM_COMBOS, hand_to_combo_indices

_RANKS = set("AKQJT98765432")


def parse_range_notation(notation: str) -> np.ndarray:
    weights = np.zeros(NUM_COMBOS, dtype=np.float64)
    entries = [e.strip() for e in notation.split(",")]
    if not any(entries):
        raise ValueError("empty range notation")
    for entry in entries:
        if not entry:
            raise ValueError("empty entry in range notation")
        cls, _, wpart = entry.partition(":")
        cls = cls.strip()
        if wpart:
            try:
                w = float(wpart)
            except ValueError as e:
                raise ValueError(f"bad weight in {entry!r}") from e
            if not 0.0 <= w <= 1.0:
                raise ValueError(f"weight out of [0,1] in {entry!r}")
        else:
            w = 1.0
        if len(cls) == 2:
            if cls[0] != cls[1]:
                raise ValueError(
                    f"{cls!r}: non-pair classes need an s/o suffix (AKs / AKo)"
                )
        elif len(cls) == 3:
            if cls[2] not in ("s", "o") or cls[0] == cls[1]:
                raise ValueError(f"bad hand class {cls!r}")
        else:
            raise ValueError(f"bad hand class {cls!r}")
        if cls[0] not in _RANKS or cls[1] not in _RANKS:
            raise ValueError(f"bad rank in {cls!r}")
        for idx in hand_to_combo_indices(cls):
            weights[idx] = w
    return weights
```

- [ ] **Step 3: Run tests, commit**

Run: `uv run --no-sync python -m pytest gto/tests/test_range_notation.py -v` — expected: all pass.

```bash
cd ~/projects
git add gto/src/gto/library/range_notation.py gto/tests/test_range_notation.py
git commit -m "feat(gto): range-notation parser (AA,AKs:0.5,KQo -> combo weights)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: GameSpec API — POST /api/solve + capabilities + /api/hu deprecation

**Files:**
- Create: `gto/src/gto/api/routers/solve.py`
- Modify: `gto/src/gto/api/main.py` (register router)
- Modify: `gto/src/gto/api/routers/hu.py` (deprecation headers)
- Test: `gto/tests/test_solve_api.py` (new)

- [ ] **Step 1: Write the router**

Create `gto/src/gto/api/routers/solve.py`:

```python
"""GameSpec solve endpoint (mode-matrix spec section 4.1/4.5).

POST /api/solve           — HU NLHE cash postflop custom solves (M1a).
GET  /api/solve/capabilities — the supported sub-matrix, iteration clamps
                               and cost classes; the UI's source of truth.

The legacy /api/hu/* endpoints are deprecated aliases of the river /
turn_river paths through this contract.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gto.library.range_notation import parse_range_notation

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)

ITER_CLAMP = {"river": (100, 50_000, 2_000), "turn_river": (100, 30_000, 10_000)}

RAKE_PRESETS = {
    "none": (0.0, 0.0),
    "site": (0.05, 3.0),
    "live": (0.10, 5.0),
}


class RakeSpec(BaseModel):
    model: Literal["none", "site", "live", "custom"] = "none"
    pct: float | None = None      # custom only
    cap_bb: float | None = None   # custom only


class SolveConfig(BaseModel):
    positions: list[str] = ["SB", "BB"]
    pot_type: Literal["srp", "3bet", "4bet"] = "srp"
    pot_bb: float = Field(gt=0)
    board: list[str]
    ranges: dict[str, str | list[float]] = {}     # keys: ip / oop
    action_tree: dict | None = None               # {bet_sizes_pct, max_raises}


class GameSpec(BaseModel):
    game: Literal["cash", "tournament"] = "cash"
    variant: Literal["nlhe", "plo"] = "nlhe"
    table: Literal["hu", "6max", "9max"] = "hu"
    stack_bb: float = Field(gt=0)
    rake: RakeSpec = RakeSpec()
    spot: Literal["preflop", "postflop", "full_hand"] = "postflop"
    config: SolveConfig
    iterations: int | None = None


CAPABILITIES = {
    "game": ["cash"],
    "variant": ["nlhe"],
    "table": ["hu"],
    "spot": ["postflop"],
    "rake_models": list(RAKE_PRESETS) + ["custom"],
    "pot_types": ["srp", "3bet", "4bet"],
    "streets": {
        "river": {"board_cards": 5, "cost": "sync", "iterations": ITER_CLAMP["river"]},
        "turn_river": {"board_cards": 4, "cost": "sync_capped", "iterations": ITER_CLAMP["turn_river"]},
        "flop": {"board_cards": 3, "cost": "async", "status": "M1b — not yet available"},
    },
    "positions": [["SB", "BB"], ["BTN", "BB"]],
}


@router.get("/solve/capabilities")
async def capabilities():
    return CAPABILITIES


def _reject_unsupported(spec: GameSpec) -> None:
    checks = [
        (spec.game != "cash", f"game={spec.game}"),
        (spec.variant != "nlhe", f"variant={spec.variant}"),
        (spec.table != "hu", f"table={spec.table}"),
        (spec.spot != "postflop", f"spot={spec.spot}"),
        (sorted(spec.config.positions) not in (["BB", "SB"], ["BB", "BTN"]),
         f"positions={spec.config.positions}"),
        (len(spec.config.board) == 3, "flop boards are M1b (async tier) — not yet available"),
        (len(spec.config.board) not in (3, 4, 5), f"board must have 4 or 5 cards, got {len(spec.config.board)}"),
    ]
    for failed, what in checks:
        if failed:
            raise HTTPException(
                422,
                detail={"unsupported": what, "see": "/api/solve/capabilities"},
            )


def _resolve_rake(r: RakeSpec) -> tuple[float, float]:
    if r.model == "custom":
        if r.pct is None or r.cap_bb is None:
            raise HTTPException(422, "custom rake requires pct and cap_bb")
        if not 0.0 <= r.pct < 0.5 or r.cap_bb < 0:
            raise HTTPException(422, "rake pct must be in [0, 0.5), cap_bb >= 0")
        return r.pct, r.cap_bb
    return RAKE_PRESETS[r.model]


def _resolve_range(v: str | list[float] | None) -> list[float] | None:
    if v is None or v == "preset" or v == "uniform":
        return None  # binding default: uniform minus blockers
    if isinstance(v, str):
        try:
            return parse_range_notation(v).tolist()
        except ValueError as e:
            raise HTTPException(422, f"bad range notation: {e}") from e
    if len(v) != 1326:
        raise HTTPException(422, f"range weight vector must have 1326 entries, got {len(v)}")
    return v


@router.post("/solve")
async def solve(spec: GameSpec):
    _reject_unsupported(spec)
    street = "river" if len(spec.config.board) == 5 else "turn_river"
    lo, hi, default = ITER_CLAMP[street]
    iters = max(lo, min(hi, spec.iterations or default))
    pct, cap_bb = _resolve_rake(spec.rake)
    ip = _resolve_range(spec.config.ranges.get("ip"))
    oop = _resolve_range(spec.config.ranges.get("oop"))
    tree = spec.config.action_tree or {}
    bet_pcts = tree.get("bet_sizes_pct")
    max_raises = tree.get("max_raises")

    loop = asyncio.get_event_loop()
    try:
        import gto_py

        if street == "river":
            raw = await loop.run_in_executor(
                _executor,
                lambda: gto_py.solve_hu_river(
                    spec.config.board, spec.config.pot_bb, spec.stack_bb, iters,
                    ip, oop, bet_pcts, max_raises, spec.config.pot_type,
                    pct or None, cap_bb if pct else None,
                ),
            )
        else:
            raw = await loop.run_in_executor(
                _executor,
                lambda: gto_py.solve_hu_turn_river(
                    spec.config.board, spec.config.pot_bb, spec.stack_bb, iters,
                    None, ip, oop, bet_pcts, bet_pcts, max_raises,
                    spec.config.pot_type, pct or None, cap_bb if pct else None,
                ),
            )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    return _envelope(raw, spec, street, iters, pct, cap_bb)


def _envelope(raw: dict, spec: GameSpec, street: str, iters: int, pct: float, cap_bb: float) -> dict:
    """Unified SolveResult (spec section 4.5). Provenance: ev <- game values,
    per-combo ev <- avg-strategy values, equity <- separate range-vs-range
    computation in the solver, exploitability <- general-sum NashConv."""
    return {
        "strategy": raw["strategy"],
        "actions": raw["actions"],
        "combo_strategies": raw["combos"],
        "ev": {
            "ip": raw["game_value_sb"],
            "oop": raw["game_value_bb"],
            "per_combo": [{"card_a": c["card_a"], "card_b": c["card_b"], "ev": c["ev"]} for c in raw["combos"]],
        },
        "equity": {"ip": raw["equity_sb"], "oop": raw["equity_bb"]},
        "frequencies": {a["action"]: a["freq"] for a in raw["strategy"]},
        "exploitability": {
            "nashconv_bb": raw["nashconv"],
            "per_hand_bb": raw["exploitability"],
            "br_gain_ip": raw["br_gain_sb"],
            "br_gain_oop": raw["br_gain_bb"],
        },
        "meta": {
            "solver": "gto-hu",
            "street": street,
            "iterations": iters,
            "elapsed_s": raw["elapsed_secs"],
            "abstraction": None,
            "rake": {"pct": pct, "cap_bb": cap_bb},
            "equilibrium_claim": True,
            "game_spec": spec.model_dump(),
        },
    }
```

- [ ] **Step 2: Register the router + deprecation headers**

In `gto/src/gto/api/main.py`: add `solve` to the router import tuple and `app.include_router(solve.router, prefix="/api")` next to the existing lines (match the file's existing style exactly — read it first).

In `gto/src/gto/api/routers/hu.py`: add a `Response` parameter to both endpoints and set headers before returning:
```python
from fastapi import APIRouter, HTTPException, Response
...
@router.post("/hu/river", response_model=RiverResponse)
async def solve_river(req: RiverRequest, response: Response):
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/solve>; rel="successor-version"'
    ...
```
(same two lines in `solve_turn_river`).

- [ ] **Step 3: Tests**

Create `gto/tests/test_solve_api.py`:

```python
"""GameSpec endpoint: capabilities, 422 matrix, envelope shape, deprecation."""

import pytest
from fastapi.testclient import TestClient

from gto.api.main import app

client = TestClient(app)

try:
    import gto_py

    HAS_BINDING = hasattr(gto_py, "solve_hu_river")
except ImportError:
    HAS_BINDING = False


def _spec(**over):
    base = {
        "stack_bb": 90.0,
        "config": {
            "pot_bb": 20.0,
            "board": ["Ah", "Kd", "7s", "2c", "9h"],
        },
    }
    base.update(over)
    return base


def test_capabilities_shape():
    r = client.get("/api/solve/capabilities")
    assert r.status_code == 200
    caps = r.json()
    assert caps["variant"] == ["nlhe"]
    assert caps["streets"]["flop"]["cost"] == "async"


@pytest.mark.parametrize(
    "over",
    [
        {"variant": "plo"},
        {"table": "6max"},
        {"game": "tournament"},
        {"spot": "preflop"},
    ],
)
def test_unsupported_axes_422_with_pointer(over):
    r = client.post("/api/solve", json=_spec(**over))
    assert r.status_code == 422
    detail = r.json()["detail"]
    if isinstance(detail, dict):
        assert detail["see"] == "/api/solve/capabilities"


def test_flop_board_is_m1b_422():
    s = _spec()
    s["config"]["board"] = ["Ah", "Kd", "7s"]
    r = client.post("/api/solve", json=s)
    assert r.status_code == 422


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_river_solve_envelope():
    s = _spec(iterations=200)
    s["rake"] = {"model": "site"}
    s["config"]["ranges"] = {"oop": "QQ,JJ", "ip": "preset"}
    r = client.post("/api/solve", json=s)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meta"]["equilibrium_claim"] is True
    assert body["meta"]["rake"] == {"pct": 0.05, "cap_bb": 3.0}
    assert body["exploitability"]["nashconv_bb"] == pytest.approx(
        body["exploitability"]["br_gain_ip"] + body["exploitability"]["br_gain_oop"]
    )
    assert 0.0 < body["equity"]["ip"] < 1.0
    # OOP range was QQ+JJ -> 12 combos in the export
    assert len(body["combo_strategies"]) == 12
    # rake leaks value
    assert body["ev"]["ip"] + body["ev"]["oop"] < 0.0


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_hu_endpoints_carry_deprecation_headers():
    r = client.post(
        "/api/hu/river",
        json={"board": ["Ah", "Kd", "7s", "2c", "9h"], "iterations": 100},
    )
    assert r.status_code == 200
    assert r.headers.get("deprecation") == "true"
```

Run: `cd ~/projects && uv run --no-sync python -m pytest gto/tests/test_solve_api.py -v`
Expected: all pass (binding-dependent ones skip if gto_py absent).

- [ ] **Step 4: Full pytest + commit**

```bash
uv run --no-sync python -m pytest gto/tests -q    # all pass
cd ~/projects
git add gto/src/gto/api/routers/solve.py gto/src/gto/api/main.py gto/src/gto/api/routers/hu.py gto/tests/test_solve_api.py
git commit -m "feat(gto-api): GameSpec POST /api/solve + capabilities + hu deprecation headers

Unified SolveResult envelope (strategy / combo_strategies / ev / equity /
frequencies / general-sum exploitability / meta with equilibrium_claim).
Unsupported mode-matrix combinations 422 with a capabilities pointer.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---### Task 10: Web — solve API client + Custom Solve form

**Files:**
- Create: `gto/web/lib/solve-api.ts`
- Create: `gto/web/app/solver/CustomSolve.tsx`
- Modify: `gto/web/app/solver/page.tsx` (mount the component)

- [ ] **Step 1: API client**

Create `gto/web/lib/solve-api.ts`:

```ts
// GameSpec client for POST /api/solve (mode-matrix M1a).

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface SolveRequest {
  stack_bb: number;
  iterations?: number;
  rake: { model: "none" | "site" | "live" };
  config: {
    pot_bb: number;
    pot_type: "srp" | "3bet" | "4bet";
    board: string[];
    ranges: { ip?: string; oop?: string };
    action_tree?: { bet_sizes_pct?: number[]; max_raises?: number };
  };
}

export interface SolveResult {
  strategy: { action: string; freq: number }[];
  actions: string[];
  combo_strategies: { card_a: string; card_b: string; freqs: number[]; ev: number }[];
  ev: { ip: number; oop: number };
  equity: { ip: number; oop: number };
  exploitability: {
    nashconv_bb: number;
    per_hand_bb: number;
    br_gain_ip: number;
    br_gain_oop: number;
  };
  meta: {
    street: string;
    iterations: number;
    elapsed_s: number;
    rake: { pct: number; cap_bb: number };
    equilibrium_claim: boolean;
  };
}

export async function customSolve(req: SolveRequest): Promise<SolveResult> {
  const res = await fetch(`${API}/api/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game: "cash", variant: "nlhe", table: "hu", spot: "postflop", ...req }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`solve failed (${res.status}): ${body}`);
  }
  return res.json();
}
```
Before writing, check how `gto/web/lib/hu-api.ts` resolves the API base (line ~44) and copy ITS convention (relative `/api` via Next rewrite vs explicit base) so dev setups keep working — adjust the `API` constant accordingly.

- [ ] **Step 2: Custom Solve component**

Create `gto/web/app/solver/CustomSolve.tsx` (client component, self-contained; match the page's existing Tailwind/neon classes by reading `gto/web/app/solver/page.tsx` and `gto/web/app/hu/page.tsx` first — reuse their card/panel class names rather than the generic ones below if they differ):

```tsx
"use client";

import { useState } from "react";
import { customSolve, SolveResult } from "@/lib/solve-api";

const DEFAULT_BOARD = "Ah Kd 7s 2c 9h";

export default function CustomSolve() {
  const [board, setBoard] = useState(DEFAULT_BOARD);
  const [potBb, setPotBb] = useState(20);
  const [stackBb, setStackBb] = useState(90);
  const [potType, setPotType] = useState<"srp" | "3bet" | "4bet">("srp");
  const [rake, setRake] = useState<"none" | "site" | "live">("none");
  const [oopRange, setOopRange] = useState("");
  const [ipRange, setIpRange] = useState("");
  const [betSizes, setBetSizes] = useState("");
  const [result, setResult] = useState<SolveResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const cards = board.trim().split(/\s+/);
  const street = cards.length === 5 ? "river" : cards.length === 4 ? "turn+river" : "unsupported";

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await customSolve({
        stack_bb: stackBb,
        rake: { model: rake },
        config: {
          pot_bb: potBb,
          pot_type: potType,
          board: cards,
          ranges: {
            ...(ipRange.trim() ? { ip: ipRange.trim() } : {}),
            ...(oopRange.trim() ? { oop: oopRange.trim() } : {}),
          },
          ...(betSizes.trim()
            ? { action_tree: { bet_sizes_pct: betSizes.split(",").map((s) => parseInt(s.trim(), 10)) } }
            : {}),
        },
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8 rounded-xl border border-cyan-500/30 bg-black/40 p-6">
      <h2 className="text-xl font-bold text-cyan-300">
        Custom Solve <span className="text-sm font-normal text-cyan-500">(gto-hu equilibrium — exact exploitability)</span>
      </h2>
      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <label className="text-sm text-cyan-200">
          Board (4=turn, 5=river)
          <input className="mt-1 w-full rounded bg-slate-900 p-2 text-white" value={board} onChange={(e) => setBoard(e.target.value)} />
        </label>
        <label className="text-sm text-cyan-200">
          Pot (bb)
          <input type="number" className="mt-1 w-full rounded bg-slate-900 p-2 text-white" value={potBb} onChange={(e) => setPotBb(+e.target.value)} />
        </label>
        <label className="text-sm text-cyan-200">
          Eff. stack (bb)
          <input type="number" className="mt-1 w-full rounded bg-slate-900 p-2 text-white" value={stackBb} onChange={(e) => setStackBb(+e.target.value)} />
        </label>
        <label className="text-sm text-cyan-200">
          Pot type
          <select className="mt-1 w-full rounded bg-slate-900 p-2 text-white" value={potType} onChange={(e) => setPotType(e.target.value as typeof potType)}>
            <option value="srp">SRP</option>
            <option value="3bet">3bet pot</option>
            <option value="4bet">4bet pot</option>
          </select>
        </label>
        <label className="text-sm text-cyan-200">
          Rake
          <select className="mt-1 w-full rounded bg-slate-900 p-2 text-white" value={rake} onChange={(e) => setRake(e.target.value as typeof rake)}>
            <option value="none">None</option>
            <option value="site">Site (5% / 3bb)</option>
            <option value="live">Live (10% / 5bb)</option>
          </select>
        </label>
        <label className="text-sm text-cyan-200">
          OOP range (blank = uniform)
          <input className="mt-1 w-full rounded bg-slate-900 p-2 text-white" placeholder="QQ,JJ,AKs:0.5" value={oopRange} onChange={(e) => setOopRange(e.target.value)} />
        </label>
        <label className="text-sm text-cyan-200">
          IP range (blank = uniform)
          <input className="mt-1 w-full rounded bg-slate-900 p-2 text-white" placeholder="AA,KK,AQo" value={ipRange} onChange={(e) => setIpRange(e.target.value)} />
        </label>
        <label className="text-sm text-cyan-200">
          Bet sizes %pot (blank = default)
          <input className="mt-1 w-full rounded bg-slate-900 p-2 text-white" placeholder="50,100" value={betSizes} onChange={(e) => setBetSizes(e.target.value)} />
        </label>
      </div>
      <button
        onClick={run}
        disabled={busy || street === "unsupported"}
        className="mt-4 rounded bg-cyan-600 px-6 py-2 font-bold text-black hover:bg-cyan-400 disabled:opacity-40"
      >
        {busy ? "Solving…" : `Solve ${street}`}
      </button>
      {street === "turn+river" && <p className="mt-2 text-xs text-amber-400">turn+river runs ~10-40 s synchronously — keep the tab open.</p>}
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      {result && (
        <div className="mt-6">
          <div className="rounded bg-emerald-900/30 p-3 text-emerald-300">
            exploitability {result.exploitability.per_hand_bb.toFixed(4)} bb/hand
            (NashConv {result.exploitability.nashconv_bb.toFixed(4)}) ·
            equity IP {(result.equity.ip * 100).toFixed(1)}% ·
            EV IP {result.ev.ip.toFixed(3)} / OOP {result.ev.oop.toFixed(3)} bb ·
            {result.meta.elapsed_s.toFixed(1)}s / {result.meta.iterations} iters
          </div>
          <table className="mt-4 w-full text-left text-sm text-cyan-100">
            <thead><tr className="text-cyan-400"><th className="p-1">OOP root action</th><th className="p-1">freq</th></tr></thead>
            <tbody>
              {result.strategy.map((s) => (
                <tr key={s.action} className="border-t border-cyan-500/20">
                  <td className="p-1">{s.action}</td>
                  <td className="p-1">{(s.freq * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 3: Mount it on the solver page**

In `gto/web/app/solver/page.tsx`: import and render `<CustomSolve />` after the existing content (read the file; if it is a server component wrapping a client part, add the import + element at the layout level that renders the page body). Add a visible label distinguishing it from the legacy section, e.g. the legacy gto-cuda block keeps its heading and CustomSolve's heading carries the "equilibrium" wording (already in the component).

- [ ] **Step 4: Build + live verification (real entry point)**

```bash
cd ~/projects/gto/web && pnpm install --silent && pnpm exec next build   # expect: build succeeds
```
Then verify through the running app (two terminals or background):
```bash
cd ~/projects/gto && uv run --no-sync uvicorn gto.api.main:app --port 8000 &   # backend
cd ~/projects/gto/web && pnpm exec next dev &                                   # frontend
```
Playwright smoke (use the document-skills:webapp-testing pattern):
```python
# /tmp/verify_custom_solve.py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto("http://localhost:3000/solver")
    page.wait_for_load_state("networkidle")
    page.get_by_text("Custom Solve").wait_for()
    page.get_by_role("button", name="Solve river").click()
    page.get_by_text("exploitability", exact=False).wait_for(timeout=120_000)
    page.screenshot(path="/tmp/custom_solve.png", full_page=True)
    b.close()
print("OK")
```
Run: `uv run --no-sync python /tmp/verify_custom_solve.py` — expected: `OK`, screenshot shows the result banner. Kill the dev servers afterwards.

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add gto/web/lib/solve-api.ts gto/web/app/solver/CustomSolve.tsx gto/web/app/solver/page.tsx
git commit -m "feat(gto-web): Custom Solve form on /solver backed by POST /api/solve

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Finalize — full suites, docs, spec status

- [ ] **Step 1: Full Rust + Python suites**

```bash
cd ~/projects/gto && source ~/.cargo/env
cargo test --manifest-path Cargo.toml 2>&1 | tail -5      # full workspace, ~3h — run in background
cd ~/projects && uv run --no-sync python -m pytest gto/tests -q
```
Expected: everything green. Quote the tail of both outputs in the report.

- [ ] **Step 2: Docs**

- `gto/PROGRESS.md`: add an M1a entry under 完了済み (date, GameSpec endpoint, rake + NashConv, PokerVariant seam, decommission list, custom solve form; note M1b pending).
- `gto/CLAUDE.md`: update the architecture table row for gto-py (mention range/rake params), remove `solve_spot_multistreet` from the bindings description, add `/api/solve` to the API row, and note the multistreet tier removal in Gotchas (replace the "gto-cuda is single-street only — use gto-core::multistreet when correctness matters" advice with "use gto-hu / POST /api/solve").
- Spec `2026-06-11-mode-matrix-roadmap-design.md`: status line → "M1a implemented (commits …); M1b pending"; note the Kuhn→degenerate-tree validation substitution in §4.2.

- [ ] **Step 3: Commit docs**

```bash
cd ~/projects
git add gto/PROGRESS.md gto/CLAUDE.md gto/docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md
git commit -m "docs(gto): record M1a custom-solve foundation completion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes (already applied)

- **Spec coverage:** §2 decommission → Task 1; §4.2 rake/exploitability → Tasks 2-4; §4.3 seam → Task 5; §4.4 bindings → Tasks 6-7; §4.1 GameSpec + ranges → Tasks 8-9; web → Task 10; §4.6 M1a criteria 1-5 → Tasks 9 (1), 3-4 (2), 5 (3), 1 (4), 9+10 (5 — concurrency overlap is already pinned by test_gil_release.py; the bounded executor IS the existing 2-worker pool, documented). M1b criteria 6-7 are OUT of this plan.
- **Known deviations from spec, both deliberate:** (a) Kuhn/Leduc+rake replaced by hand-checkable degenerate river trees (Kuhn runs on ScalarCfr which has no rake) — recorded in spec via Task 11; (b) acceptance 4.3(b) reworded (Task 5) per the rev-2 review finding that the literal criterion was vacuous.
- **Type consistency:** `with_rake` constructor order is `(tree, board, ranges, variant, rake)` for VectorRiverSolver and `(tree, board, ranges, variant, mode, rake)` for TurnRiverSolver; `HuSolveOutput.combo_data` is a 4-tuple everywhere after Task 6 (Task 6 step 3 updates turn_river's closure in the same commit so the shared struct never breaks).
- **Risk callouts for the implementer:** (1) check-only StreetConfig in Tasks 3-4 assumes the tree builder accepts an empty bet list — if it panics, STOP and report (do not silently change the builder). (2) `Card` newtype adaptation in Task 5 step 1 — copy the convention from `showdown.rs:18`. (3) Task 10 class names are placeholders to be matched to the real page's styling.
