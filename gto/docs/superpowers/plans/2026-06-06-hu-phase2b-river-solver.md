# HU Solver Phase 2b: Vector River Solver, Differential Tests & CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Production vector CFR solver for exact HU river spots (1326 combos, blocker-exact showdowns, exact best response in bb/hand), differential-tested against the Phase 2a scalar engine, exposed via the `solve-hu-river` CLI with CSV/JSON export.

**Architecture:** `VectorRiverSolver` traverses the Phase 2a `Tree` with per-combo value vectors (counterfactual formulation: opponent reach and chance fold into the value sums). Showdown is O(N) per terminal via strength-sorted prefix sums with per-card blocker correction (order precomputed once). `TinyRiver` adapts the same `Tree` + payoff code to the scalar `Game` trait so both engines are compared on identical inputs.

**Tech Stack:** Rust 2021, no new dependencies. Reuses Phase 1's `gto_core::eval::{showdown_strengths, evaluate_best}` and all Phase 2a types.

**Prerequisite:** Phases 1 and 2a complete and green.

---

### Task 1: `TinyRiver` — the river tree as a scalar `Game`

**Files:**
- Create: `gto/crates/gto-hu/src/games/tiny_river.rs`
- Modify: `gto/crates/gto-hu/src/games/mod.rs`
- Create: `gto/crates/gto-hu/tests/test_tiny_river.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_tiny_river.rs`:

```rust
use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::TinyRiver;
use gto_hu::solver::{CfrVariant, Game, ScalarCfr};
use gto_hu::tree::{build_river_tree, StreetConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 { parse_card(s).unwrap() }

fn nuts_vs_bluffcatcher() -> TinyRiver {
    // Board 2c 7d 9h Jh Kd: QT = nut straight, no flush possible.
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let tree = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    TinyRiver::new(
        tree,
        board,
        [
            vec![(c("Qc"), c("Tc")), (c("4s"), c("3s"))], // OOP: nuts or air
            vec![(c("Kh"), c("Qh"))],                     // IP: bluff catcher
        ],
    )
}

#[test]
fn chance_outcomes_are_uniform_and_card_safe() {
    let g = nuts_vs_bluffcatcher();
    let deals = g.chance_outcomes(&g.root());
    assert_eq!(deals.len(), 2, "2 OOP hands × 1 IP hand, no blocker overlap");
    let total: f64 = deals.iter().map(|(_, p)| p).sum();
    assert!((total - 1.0).abs() < 1e-12);
}

#[test]
fn polarized_oop_bets_nuts_and_solver_converges() {
    let g = nuts_vs_bluffcatcher();
    let mut cfr = ScalarCfr::new(&g, CfrVariant::cfr_plus_default());
    cfr.run(5_000);
    let expl = exploitability(&g, &cfr);
    assert!(expl < 0.05, "exploitability {expl:.4} bb should be < 0.05");
    // OOP root infoset for the nuts (hand index 0), root node id 0.
    // Actions: [check, bet15, bet30, allin90] — nuts must rarely check.
    let s = cfr.average_strategy("1|0|0", 4);
    assert!(s[0] < 0.05, "nuts check freq {} should be ~0", s[0]);
}

#[test]
fn zero_sum_at_every_terminal() {
    let g = nuts_vs_bluffcatcher();
    // Walk the whole game; at terminals payoffs must sum to 0.
    fn walk(g: &TinyRiver, s: &<TinyRiver as Game>::State) {
        if g.is_terminal(s) {
            let p0 = g.payoff(s, 0);
            let p1 = g.payoff(s, 1);
            assert!((p0 + p1).abs() < 1e-9, "not zero-sum: {p0} + {p1}");
            return;
        }
        if g.is_chance(s) {
            for (cs, _) in g.chance_outcomes(s) {
                walk(g, &cs);
            }
            return;
        }
        for a in 0..g.num_actions(s) {
            walk(g, &g.next(s, a));
        }
    }
    walk(&g, &g.root());
}
```

Note: the infoset key format `"{player}|{hand_idx}|{node_id}"` is defined in
Step 3; OOP is player 1 (`PLAYER_BB`) and acts at root node 0, hence
`"1|0|0"`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_tiny_river`
Expected: COMPILE FAIL (`TinyRiver` missing).

- [ ] **Step 3: Implement**

Create `gto/crates/gto-hu/src/games/tiny_river.rs`:

```rust
use gto_core::eval::evaluate_best;

use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::solver::Game;
use crate::tree::{NodeKind, Tree};

/// The river `Tree` played with small explicit hand lists — a scalar
/// reference game for differential-testing the vector solver.
pub struct TinyRiver {
    pub tree: Tree,
    pub board: [u8; 5],
    /// hands[p] = player p's combos (card_a, card_b), all distinct from the
    /// board. Player indices match the tree (0 = SB/IP, 1 = BB/OOP).
    pub hands: [Vec<(u8, u8)>; 2],
}

#[derive(Debug, Clone)]
pub struct TinyRiverState {
    /// (index into hands[0], index into hands[1]); usize::MAX = undealt.
    pub deal: (usize, usize),
    pub node: usize,
}

impl TinyRiver {
    pub fn new(tree: Tree, board: [u8; 5], hands: [Vec<(u8, u8)>; 2]) -> Self {
        for hs in &hands {
            for &(a, b) in hs {
                assert!(a != b && !board.contains(&a) && !board.contains(&b),
                    "hand cards must be distinct and off-board");
            }
        }
        TinyRiver { tree, board, hands }
    }

    fn strength(&self, hand: (u8, u8)) -> u16 {
        let mut cards = [0u8; 7];
        cards[0] = hand.0;
        cards[1] = hand.1;
        cards[2..7].copy_from_slice(&self.board);
        evaluate_best(&cards)
    }
}

impl Game for TinyRiver {
    type State = TinyRiverState;

    fn root(&self) -> TinyRiverState {
        TinyRiverState { deal: (usize::MAX, usize::MAX), node: 0 }
    }

    fn is_chance(&self, s: &TinyRiverState) -> bool {
        s.deal.0 == usize::MAX
    }

    fn chance_outcomes(&self, s: &TinyRiverState) -> Vec<(TinyRiverState, f64)> {
        let mut out = Vec::new();
        for (i, &(a0, b0)) in self.hands[0].iter().enumerate() {
            for (j, &(a1, b1)) in self.hands[1].iter().enumerate() {
                let clash = a0 == a1 || a0 == b1 || b0 == a1 || b0 == b1;
                if !clash {
                    out.push((TinyRiverState { deal: (i, j), node: s.node }, 0.0));
                }
            }
        }
        let p = 1.0 / out.len() as f64;
        for o in &mut out {
            o.1 = p;
        }
        out
    }

    fn is_terminal(&self, s: &TinyRiverState) -> bool {
        !self.is_chance(s)
            && matches!(
                self.tree.nodes[s.node].kind,
                NodeKind::FoldTerminal { .. } | NodeKind::Showdown
            )
    }

    fn payoff(&self, s: &TinyRiverState, player: usize) -> f64 {
        let node = &self.tree.nodes[s.node];
        let cbb = match node.kind {
            NodeKind::FoldTerminal { winner } => fold_payoffs(&node.state, winner)[player],
            NodeKind::Showdown => {
                let s0 = self.strength(self.hands[0][s.deal.0]);
                let s1 = self.strength(self.hands[1][s.deal.1]);
                let winner = match s0.cmp(&s1) {
                    std::cmp::Ordering::Greater => Some(0),
                    std::cmp::Ordering::Less => Some(1),
                    std::cmp::Ordering::Equal => None,
                };
                showdown_payoffs(&node.state, winner)[player]
            }
            NodeKind::Action { .. } => unreachable!("payoff at non-terminal"),
        };
        cbb as f64 / 100.0 // bb
    }

    fn player(&self, s: &TinyRiverState) -> usize {
        match self.tree.nodes[s.node].kind {
            NodeKind::Action { actor } => actor as usize,
            _ => unreachable!("player() at non-action node"),
        }
    }

    fn num_actions(&self, s: &TinyRiverState) -> usize {
        self.tree.nodes[s.node].children.len()
    }

    fn next(&self, s: &TinyRiverState, action: usize) -> TinyRiverState {
        TinyRiverState { deal: s.deal, node: self.tree.nodes[s.node].children[action].1 }
    }

    fn infoset_key(&self, s: &TinyRiverState) -> String {
        let p = self.player(s);
        let hand_idx = if p == 0 { s.deal.0 } else { s.deal.1 };
        // node id encodes the full betting history (tree is fixed).
        format!("{p}|{hand_idx}|{}", s.node)
    }
}
```

Update `src/games/mod.rs`:

```rust
pub mod kuhn;
pub mod leduc;
pub mod tiny_river;

pub use kuhn::Kuhn;
pub use leduc::Leduc;
pub use tiny_river::TinyRiver;
```

Also export `Game` from the solver module if not already
(`pub use scalar::{Game, InfoNode, ScalarCfr};` in `src/solver/mod.rs` —
done in Phase 2a Task 7).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_tiny_river`
Expected: 3 PASS. Quote the exploitability line.

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): TinyRiver scalar reference game over the river tree"
```

---

### Task 2: Vector river solver

**Files:**
- Create: `gto/crates/gto-hu/src/solver/vector.rs`
- Modify: `gto/crates/gto-hu/src/solver/mod.rs`
- Create: `gto/crates/gto-hu/tests/test_river_solver.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_river_solver.rs`:

```rust
use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{combo_index, uniform_excluding, Range, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};

fn c(s: &str) -> u8 { parse_card(s).unwrap() }

fn board() -> [u8; 5] {
    [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")]
}

fn uniform_solver(variant: CfrVariant) -> VectorRiverSolver {
    let tree = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let b = board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    VectorRiverSolver::new(tree, b, ranges, variant)
}

#[test]
fn strategies_sum_to_one_for_active_combos() {
    let mut s = uniform_solver(CfrVariant::cfr_plus_default());
    s.run(50);
    for node_id in s.action_node_ids() {
        for combo in 0..NUM_COMBOS {
            if s.ranges[s.actor_at(node_id) as usize].weights[combo] == 0.0 {
                continue;
            }
            let strat = s.average_strategy(node_id, combo);
            let sum: f64 = strat.iter().sum();
            assert!(
                (sum - 1.0).abs() < 1e-9,
                "node {node_id} combo {combo}: strategy sums to {sum}"
            );
        }
    }
}

#[test]
fn exploitability_decreases_with_iterations() {
    let mut s = uniform_solver(CfrVariant::cfr_plus_default());
    s.run(20);
    let e1 = s.exploitability_bb();
    s.run(480);
    let e2 = s.exploitability_bb();
    assert!(e1.exploitability >= -1e-9 && e2.exploitability >= -1e-9);
    assert!(
        e2.exploitability < e1.exploitability,
        "exploitability must fall: {:.4} → {:.4}",
        e1.exploitability, e2.exploitability
    );
    assert!(e2.exploitability < 0.30, "after 500 iters: {:.4} bb", e2.exploitability);
}

#[test]
fn nuts_never_folds_to_a_bet() {
    // QT (nut straight) facing the root 15bb bet must never fold.
    let mut s = uniform_solver(CfrVariant::cfr_plus_default());
    s.run(300);
    let qt = combo_index(c("Qc"), c("Tc"));
    // Root child 1 = bet 15bb → IP response node.
    let resp = s.tree.nodes[0].children[1].1;
    let strat = s.average_strategy(resp, qt);
    assert!(strat[0] < 0.01, "QT fold freq vs bet = {} (must be ~0)", strat[0]);
}

#[test]
fn blocked_combos_keep_zero_reach() {
    let s = uniform_solver(CfrVariant::cfr_plus_default());
    let kd_combo = combo_index(c("Kd"), c("Ks"));
    assert_eq!(s.ranges[0].weights[kd_combo], 0.0);
    assert_eq!(s.ranges[1].weights[kd_combo], 0.0);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_river_solver`
Expected: COMPILE FAIL.

- [ ] **Step 3: Implement the solver**

Create `gto/crates/gto-hu/src/solver/vector.rs`:

```rust
use gto_core::eval::showdown_strengths;

use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::ranges::{all_combos, Range, NUM_COMBOS};
use crate::tree::{NodeKind, Tree};
use super::regret::regret_matching;
use super::variant::CfrVariant;

const N: usize = NUM_COMBOS;

/// Best-response report in bb/hand.
#[derive(Debug, Clone, Copy)]
pub struct ExplReport {
    pub br_value: [f64; 2],
    /// (br0 + br1) / 2 — NashConv/2, 0 at equilibrium.
    pub exploitability: f64,
}

/// Exact-combo vector CFR for a fixed river board.
/// Values are counterfactual: each per-combo value already sums the
/// opponent's reach-weighted outcomes (blockers handled exactly).
pub struct VectorRiverSolver {
    pub tree: Tree,
    pub board: [u8; 5],
    pub ranges: [Range; 2],
    pub variant: CfrVariant,
    /// [node][action * N + combo]
    regrets: Vec<Vec<f64>>,
    strat_sum: Vec<Vec<f64>>,
    strengths: Vec<u16>,
    /// Combo indices with strength > 0, sorted ascending by strength.
    sorted_idx: Vec<usize>,
    iteration: u32,
}

impl VectorRiverSolver {
    pub fn new(tree: Tree, board: [u8; 5], mut ranges: [Range; 2], variant: CfrVariant) -> Self {
        for r in &mut ranges {
            r.remove_blockers(&board);
        }
        let strengths = showdown_strengths(&board);
        let mut sorted_idx: Vec<usize> = (0..N).filter(|&i| strengths[i] > 0).collect();
        sorted_idx.sort_unstable_by_key(|&i| strengths[i]);
        let alloc = |tree: &Tree| -> Vec<Vec<f64>> {
            tree.nodes
                .iter()
                .map(|n| vec![0.0; n.children.len().max(1) * N])
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        VectorRiverSolver {
            tree, board, ranges, variant, regrets, strat_sum, strengths, sorted_idx,
            iteration: 0,
        }
    }

    pub fn run(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;
                self.traverse(0, traverser, &reach, &opp);
            }
        }
    }

    /// Counterfactual values (bb) for `traverser`'s combos.
    fn traverse(
        &mut self,
        node_id: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let kind = self.tree.nodes[node_id].kind;
        match kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[traverser as usize] as f64 / 100.0;
                let compat = weighted_compat(opp_reach);
                compat.iter().map(|w| pay * w).collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                // Winner nets the opponent's (equal) contribution.
                let win_bb =
                    showdown_payoffs(&state, Some(traverser))[traverser as usize] as f64 / 100.0;
                let diff = self.showdown_diff(opp_reach);
                diff.iter().map(|d| win_bb * d).collect()
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let strat = self.node_strategy(node_id, na);

                if actor == traverser {
                    let mut action_vals: Vec<Vec<f64>> = Vec::with_capacity(na);
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut nr = *reach;
                        for c in 0..N {
                            nr[c] *= strat[a * N + c];
                        }
                        action_vals.push(self.traverse(child, traverser, &nr, opp_reach));
                    }
                    let mut ev = vec![0.0; N];
                    for c in 0..N {
                        for (a, av) in action_vals.iter().enumerate() {
                            ev[c] += strat[a * N + c] * av[c];
                        }
                    }
                    let t = self.iteration;
                    let (sd, sw) =
                        (self.variant.strategy_discount(t), self.variant.strategy_weight(t));
                    let variant = self.variant;
                    let reg = &mut self.regrets[node_id];
                    let ssum = &mut self.strat_sum[node_id];
                    for c in 0..N {
                        if reach[c] == 0.0 && opp_reach[c] == 0.0 {
                            continue;
                        }
                        for a in 0..na {
                            let i = a * N + c;
                            reg[i] = variant.update_regret(reg[i], action_vals[a][c] - ev[c], t);
                            ssum[i] = ssum[i] * sd + sw * reach[c] * strat[i];
                        }
                    }
                    ev
                } else {
                    let mut ev = vec![0.0; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] *= strat[a * N + c];
                        }
                        let av = self.traverse(child, traverser, reach, &no);
                        for c in 0..N {
                            ev[c] += av[c];
                        }
                    }
                    ev
                }
            }
        }
    }

    /// Current per-combo strategy at a node: [action * N + combo].
    fn node_strategy(&self, node_id: usize, na: usize) -> Vec<f64> {
        let reg = &self.regrets[node_id];
        let mut strat = vec![0.0; na * N];
        let mut r = vec![0.0; na];
        let mut s = vec![0.0; na];
        for c in 0..N {
            for a in 0..na {
                r[a] = reg[a * N + c];
            }
            regret_matching(&r, &mut s);
            for a in 0..na {
                strat[a * N + c] = s[a];
            }
        }
        strat
    }

    /// win_w − lose_w per combo against `opp_reach`, blocker-exact.
    /// O(N) per call using the precomputed strength order.
    fn showdown_diff(&self, opp_reach: &[f64; N]) -> Vec<f64> {
        let combos = all_combos();
        let idx = &self.sorted_idx;
        let mut out = vec![0.0; N];

        // Ascending sweep: cum sums over strictly weaker tiers → win_w.
        let mut cum = 0.0f64;
        let mut cum_card = [0.0f64; 52];
        let mut g = 0;
        while g < idx.len() {
            let s = self.strengths[idx[g]];
            let mut h = g;
            while h < idx.len() && self.strengths[idx[h]] == s {
                h += 1;
            }
            for &i in &idx[g..h] {
                let (a, b) = combos[i];
                out[i] += cum - cum_card[a as usize] - cum_card[b as usize];
            }
            for &i in &idx[g..h] {
                let w = opp_reach[i];
                if w != 0.0 {
                    let (a, b) = combos[i];
                    cum += w;
                    cum_card[a as usize] += w;
                    cum_card[b as usize] += w;
                }
            }
            g = h;
        }

        // Descending sweep: cum sums over strictly stronger tiers → −lose_w.
        let mut cum = 0.0f64;
        let mut cum_card = [0.0f64; 52];
        let mut g = idx.len();
        while g > 0 {
            let s = self.strengths[idx[g - 1]];
            let mut start = g;
            while start > 0 && self.strengths[idx[start - 1]] == s {
                start -= 1;
            }
            for &i in &idx[start..g] {
                let (a, b) = combos[i];
                out[i] -= cum - cum_card[a as usize] - cum_card[b as usize];
            }
            for &i in &idx[start..g] {
                let w = opp_reach[i];
                if w != 0.0 {
                    let (a, b) = combos[i];
                    cum += w;
                    cum_card[a as usize] += w;
                    cum_card[b as usize] += w;
                }
            }
            g = start;
        }
        out
    }

    // ----- Introspection / outputs -------------------------------------

    pub fn action_node_ids(&self) -> Vec<usize> {
        (0..self.tree.nodes.len())
            .filter(|&i| matches!(self.tree.nodes[i].kind, NodeKind::Action { .. }))
            .collect()
    }

    pub fn actor_at(&self, node_id: usize) -> u8 {
        match self.tree.nodes[node_id].kind {
            NodeKind::Action { actor } => actor,
            _ => panic!("not an action node"),
        }
    }

    /// Normalized average strategy for one combo at one node.
    pub fn average_strategy(&self, node_id: usize, combo: usize) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        let ssum = &self.strat_sum[node_id];
        let total: f64 = (0..na).map(|a| ssum[a * N + combo]).sum();
        if total > 0.0 {
            (0..na).map(|a| ssum[a * N + combo] / total).collect()
        } else {
            vec![1.0 / na as f64; na]
        }
    }

    /// Range-weighted aggregate strategy at a node (for display).
    pub fn aggregate_strategy(&self, node_id: usize) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[node_id];
        let actor = self.actor_at(node_id) as usize;
        let na = node.children.len();
        let mut freq = vec![0.0; na];
        let mut total = 0.0;
        for c in 0..N {
            let w = self.ranges[actor].weights[c];
            if w == 0.0 {
                continue;
            }
            let s = self.average_strategy(node_id, c);
            for a in 0..na {
                freq[a] += w * s[a];
            }
            total += w;
        }
        if total > 0.0 {
            for f in &mut freq {
                *f /= total;
            }
        }
        node.children
            .iter()
            .zip(freq)
            .map(|((act, _), f)| (act.label(), f))
            .collect()
    }

    // ----- Exact best response ------------------------------------------

    /// Counterfactual BR values for `br_player` (opponent plays the
    /// average strategy).
    fn br_values(&self, node_id: usize, br_player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        let kind = self.tree.nodes[node_id].kind;
        match kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[br_player as usize] as f64 / 100.0;
                weighted_compat(opp_reach).iter().map(|w| pay * w).collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(br_player))[br_player as usize] as f64 / 100.0;
                self.showdown_diff(opp_reach).iter().map(|d| win_bb * d).collect()
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                if actor == br_player {
                    let mut best = vec![f64::NEG_INFINITY; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.br_values(child, br_player, opp_reach);
                        for c in 0..N {
                            if v[c] > best[c] {
                                best[c] = v[c];
                            }
                        }
                    }
                    best
                } else {
                    let mut ev = vec![0.0; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            let s = self.average_strategy(node_id, c);
                            no[c] = opp_reach[c] * s[a];
                        }
                        let v = self.br_values(child, br_player, &no);
                        for c in 0..N {
                            ev[c] += v[c];
                        }
                    }
                    ev
                }
            }
        }
    }

    /// Exploitability in bb/hand: (BR_sb + BR_bb) / 2.
    pub fn exploitability_bb(&self) -> ExplReport {
        let mut br_value = [0.0f64; 2];
        for p in 0..2usize {
            let own = self.ranges[p].weights;
            let opp = self.ranges[1 - p].weights;
            let vals = self.br_values(0, p as u8, &opp);
            let compat = weighted_compat(&opp);
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
        ExplReport {
            br_value,
            exploitability: (br_value[0] + br_value[1]) / 2.0,
        }
    }
}

/// For each combo c: Σ over opponent combos compatible with c of their
/// weight (total − per-card sums + own-combo weight added back).
fn weighted_compat(opp_reach: &[f64; N]) -> Vec<f64> {
    let combos = all_combos();
    let total: f64 = opp_reach.iter().sum();
    let mut per_card = [0.0f64; 52];
    for (i, &(a, b)) in combos.iter().enumerate() {
        let w = opp_reach[i];
        if w != 0.0 {
            per_card[a as usize] += w;
            per_card[b as usize] += w;
        }
    }
    combos
        .iter()
        .enumerate()
        .map(|(i, &(a, b))| total - per_card[a as usize] - per_card[b as usize] + opp_reach[i])
        .collect()
}
```

Performance note for the implementer: `br_values` recomputes
`average_strategy` per combo inside the opponent loop — O(na²·N) per node,
fine at river scale. Do not optimize prematurely.

Update `src/solver/mod.rs`:

```rust
pub mod regret;
pub mod scalar;
pub mod variant;
pub mod vector;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use variant::CfrVariant;
pub use vector::{ExplReport, VectorRiverSolver};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_river_solver`
Expected: 4 PASS (~tens of seconds for the 500-iteration test in debug;
if slow, run with `--release`: `cargo test -p gto-hu --release`). Quote
the exploitability values in the task report.

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): exact-combo vector CFR river solver with blocker-exact O(N) showdown and exact best response"
```

---

### Task 3: Differential test — scalar vs vector must agree

**Files:**
- Create: `gto/crates/gto-hu/tests/test_differential.rs`

- [ ] **Step 1: Write the test**

Create `gto/crates/gto-hu/tests/test_differential.rs`:

```rust
//! Differential test (mandatory per spec): the scalar reference engine and
//! the vector production engine must converge to the same equilibrium on
//! identical tiny river spots.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::TinyRiver;
use gto_hu::ranges::{combo_index, Range, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, ScalarCfr, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 { parse_card(s).unwrap() }

#[test]
fn scalar_and_vector_agree_on_tiny_spot() {
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let hands0 = vec![(c("Qc"), c("Tc")), (c("4s"), c("3s")), (c("Ah"), c("Ad"))];
    let hands1 = vec![(c("Kh"), c("Qh")), (c("8s"), c("8d")), (c("Qs"), c("Ts"))];
    let iters = 3_000;
    let variant = CfrVariant::cfr_plus_default();

    // Scalar reference. Note: tree player 0 = SB/IP, player 1 = BB/OOP.
    let tree_s = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let game = TinyRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, variant);
    scalar.run(iters);
    let scalar_expl = exploitability(&game, &scalar);

    // Vector production engine with the same combos as a 0/1 range.
    let tree_v = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector = VectorRiverSolver::new(tree_v, board, [r0, r1], variant);
    vector.run(iters);
    let vector_expl = vector.exploitability_bb();

    // 1. Both must be near-equilibrium.
    assert!(scalar_expl < 0.02, "scalar exploitability {scalar_expl:.4}");
    assert!(
        vector_expl.exploitability < 0.02,
        "vector exploitability {:.4}", vector_expl.exploitability
    );

    // 2. Per-combo average strategies must match at every action node.
    //    Scalar infoset key: "{player}|{hand_idx}|{node_id}".
    for node_id in vector.action_node_ids() {
        let actor = vector.actor_at(node_id) as usize;
        let hands = if actor == 0 { &hands0 } else { &hands1 };
        let na = vector.tree.nodes[node_id].children.len();
        for (hi, &(a, b)) in hands.iter().enumerate() {
            let key = format!("{actor}|{hi}|{node_id}");
            let ss = scalar.average_strategy(&key, na);
            let vs = vector.average_strategy(node_id, combo_index(a, b));
            for ai in 0..na {
                assert!(
                    (ss[ai] - vs[ai]).abs() < 0.05,
                    "node {node_id} hand {hi} action {ai}: scalar {:.4} vs vector {:.4}",
                    ss[ai], vs[ai]
                );
            }
        }
    }
    eprintln!(
        "differential OK: scalar expl {scalar_expl:.5} bb, vector expl {:.5} bb",
        vector_expl.exploitability
    );
}

#[test]
fn vector_handles_blocker_overlap_like_scalar() {
    // Hands that block each other (QcTc vs QsTs share nothing, but add
    // KhQh vs QcTc? — use an explicit overlap: both players hold Qx).
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let hands0 = vec![(c("Qc"), c("Tc")), (c("Qd"), c("Td"))];
    let hands1 = vec![(c("Qh"), c("Th")), (c("8s"), c("8d"))];
    // Deals where both hold a Q+T are still compatible (different suits);
    // the point is identical chance support in both engines.
    let tree_s = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let game = TinyRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    scalar.run(2_000);

    let tree_v = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 { r0.weights[combo_index(a, b)] = 1.0; }
    for &(a, b) in &hands1 { r1.weights[combo_index(a, b)] = 1.0; }
    let mut vector = VectorRiverSolver::new(tree_v, board, [r0, r1], CfrVariant::cfr_plus_default());
    vector.run(2_000);

    let root_scalar = scalar.average_strategy("1|0|0", 4);
    let root_vector = vector.average_strategy(0, combo_index(c("Qh"), c("Th")));
    for ai in 0..4 {
        assert!(
            (root_scalar[ai] - root_vector[ai]).abs() < 0.05,
            "action {ai}: scalar {:.4} vs vector {:.4}",
            root_scalar[ai], root_vector[ai]
        );
    }
}
```

- [ ] **Step 2: Run the differential tests**

Run: `cargo test -p gto-hu --release --test test_differential`
Expected: 2 PASS. If strategies disagree beyond tolerance, **stop and
debug** (superpowers:systematic-debugging) — this is the core correctness
gate of Phase 2; do not loosen tolerances to pass.

- [ ] **Step 3: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "test(gto-hu): differential tests pinning vector solver to scalar reference"
```

---

### Task 4: Reports — tree stats, solver stats, CSV/JSON export

**Files:**
- Create: `gto/crates/gto-hu/src/reports/mod.rs`
- Create: `gto/crates/gto-hu/tests/test_reports.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_reports.rs`:

```rust
use gto_hu::game::BB;
use gto_hu::reports::{tree_stats, TreeStats};
use gto_hu::tree::{build_river_tree, StreetConfig};

#[test]
fn tree_stats_counts_node_kinds() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let s: TreeStats = tree_stats(&t);
    assert_eq!(
        s.action_nodes + s.fold_terminals + s.showdown_terminals,
        s.total_nodes
    );
    assert!(s.action_nodes > 0 && s.fold_terminals > 0 && s.showdown_terminals > 0);
    assert!(s.memory_estimate_bytes > 0);
}
```

- [ ] **Step 2: Run to verify failure**

Run: `cargo test -p gto-hu --test test_reports`
Expected: COMPILE FAIL.

- [ ] **Step 3: Implement**

Create `gto/crates/gto-hu/src/reports/mod.rs`:

```rust
//! Tree/solver statistics and strategy export (CSV + minimal JSON).

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use crate::ranges::{all_combos, NUM_COMBOS};
use crate::solver::{ExplReport, VectorRiverSolver};
use crate::tree::{NodeKind, Tree};

#[derive(Debug, Clone, Copy)]
pub struct TreeStats {
    pub total_nodes: usize,
    pub action_nodes: usize,
    pub fold_terminals: usize,
    pub showdown_terminals: usize,
    /// regrets + strategy sums, 8 bytes each, per (node, action, combo).
    pub memory_estimate_bytes: usize,
}

pub fn tree_stats(tree: &Tree) -> TreeStats {
    let mut s = TreeStats {
        total_nodes: tree.nodes.len(),
        action_nodes: 0,
        fold_terminals: 0,
        showdown_terminals: 0,
        memory_estimate_bytes: 0,
    };
    for n in &tree.nodes {
        match n.kind {
            NodeKind::Action { .. } => {
                s.action_nodes += 1;
                s.memory_estimate_bytes += 2 * 8 * n.children.len() * NUM_COMBOS;
            }
            NodeKind::FoldTerminal { .. } => s.fold_terminals += 1,
            NodeKind::Showdown => s.showdown_terminals += 1,
        }
    }
    s
}

#[derive(Debug, Clone)]
pub struct SolverStats {
    pub iterations: u32,
    pub elapsed_secs: f64,
    pub expl: ExplReport,
    pub root_strategy: Vec<(String, f64)>,
}

fn card_str(c: u8) -> String {
    let ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
    let suits = ['c', 'd', 'h', 's'];
    format!("{}{}", ranks[(c / 4) as usize], suits[(c % 4) as usize])
}

/// One CSV row per (node, combo, action) with avg frequency > 0.001.
pub fn write_strategy_csv(path: &Path, solver: &VectorRiverSolver) -> std::io::Result<()> {
    let combos = all_combos();
    let mut out = String::from("node_id,actor,combo,action,freq\n");
    for node_id in solver.action_node_ids() {
        let actor = solver.actor_at(node_id);
        let node = &solver.tree.nodes[node_id];
        for c in 0..NUM_COMBOS {
            if solver.ranges[actor as usize].weights[c] == 0.0 {
                continue;
            }
            let strat = solver.average_strategy(node_id, c);
            for (a, (act, _)) in node.children.iter().enumerate() {
                if strat[a] > 0.001 {
                    let (ca, cb) = combos[c];
                    let _ = writeln!(
                        out,
                        "{node_id},{actor},{}{},{},{:.4}",
                        card_str(ca), card_str(cb), act.label(), strat[a]
                    );
                }
            }
        }
    }
    fs::write(path, out)
}

/// Minimal flat JSON summary (no external deps).
pub fn write_summary_json(
    path: &Path,
    board: &[u8; 5],
    stats: &SolverStats,
    ts: &TreeStats,
) -> std::io::Result<()> {
    let board_s: String = board.iter().map(|&c| card_str(c)).collect();
    let root: String = stats
        .root_strategy
        .iter()
        .map(|(a, f)| format!("{{\"action\":\"{a}\",\"freq\":{f:.5}}}"))
        .collect::<Vec<_>>()
        .join(",");
    let json = format!(
        concat!(
            "{{\"solver\":\"gto-hu vector river (abstract HU NLHE equilibrium solver)\",",
            "\"board\":\"{}\",\"iterations\":{},\"elapsed_secs\":{:.2},",
            "\"exploitability_bb\":{:.6},\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},",
            "\"tree\":{{\"nodes\":{},\"action_nodes\":{},\"fold_terminals\":{},",
            "\"showdowns\":{},\"memory_bytes\":{}}},\"root_strategy\":[{}]}}\n"
        ),
        board_s, stats.iterations, stats.elapsed_secs,
        stats.expl.exploitability, stats.expl.br_value[0], stats.expl.br_value[1],
        ts.total_nodes, ts.action_nodes, ts.fold_terminals,
        ts.showdown_terminals, ts.memory_estimate_bytes, root,
    );
    fs::write(path, json)
}
```

- [ ] **Step 4: Run tests**

Run: `cargo test -p gto-hu --test test_reports`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): tree/solver stats and CSV/JSON strategy export"
```

---

### Task 5: `solve-hu-river` CLI

**Files:**
- Modify: `gto/crates/gto-hu/src/bin/solve_river.rs` (replace the stub)

- [ ] **Step 1: Implement**

Replace `gto/crates/gto-hu/src/bin/solve_river.rs` with:

```rust
//! solve-hu-river — exact-combo HU river solver (abstract action set).
//!
//! Example:
//!   solve-hu-river --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{tree_stats, write_strategy_csv, write_summary_json, SolverStats};
use gto_hu::solver::{CfrVariant, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-river --board AhKd7s2c9h --pot <bb> --stack <bb> \
         [--iterations N=10000] [--variant cfr+|dcfr] [--out DIR]"
    );
    exit(2);
}

fn parse_board(s: &str) -> Result<[u8; 5], String> {
    if s.len() != 10 {
        return Err(format!("board must be 10 chars (5 cards), got '{s}'"));
    }
    let mut board = [0u8; 5];
    for i in 0..5 {
        let cs = &s[i * 2..i * 2 + 2];
        board[i] = parse_card(cs).ok_or_else(|| format!("bad card '{cs}'"))?;
    }
    let mut seen = [false; 52];
    for &card in &board {
        if seen[card as usize] {
            return Err(format!("duplicate card in board '{s}'"));
        }
        seen[card as usize] = true;
    }
    Ok(board)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board: Option<[u8; 5]> = None;
    let mut pot_bb: Option<f64> = None;
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 10_000;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut out_dir: Option<PathBuf> = None;
    let mut board_raw = String::new();

    let mut i = 0;
    while i < args.len() {
        let need = |i: usize| args.get(i + 1).cloned().unwrap_or_else(|| usage());
        match args[i].as_str() {
            "--board" => {
                board_raw = need(i);
                board = Some(parse_board(&board_raw).unwrap_or_else(|e| {
                    eprintln!("error: {e}");
                    exit(2);
                }));
                i += 2;
            }
            "--pot" => { pot_bb = need(i).parse().ok(); i += 2; }
            "--stack" => { stack_bb = need(i).parse().ok(); i += 2; }
            "--iterations" => { iterations = need(i).parse().unwrap_or_else(|_| usage()); i += 2; }
            "--variant" => {
                variant = match need(i).as_str() {
                    "cfr+" => CfrVariant::cfr_plus_default(),
                    "dcfr" => CfrVariant::dcfr_default(),
                    v => { eprintln!("unknown variant '{v}'"); exit(2); }
                };
                i += 2;
            }
            "--out" => { out_dir = Some(PathBuf::from(need(i))); i += 2; }
            _ => usage(),
        }
    }
    let (Some(board), Some(pot_bb), Some(stack_bb)) = (board, pot_bb, stack_bb) else {
        usage()
    };
    let pot = (pot_bb * BB as f64).round() as i64;
    let stack = (stack_bb * BB as f64).round() as i64;
    if pot <= 0 || pot % 2 != 0 || stack <= 0 {
        eprintln!("error: pot must be positive and split evenly; stack must be positive");
        exit(2);
    }

    let tree = build_river_tree(pot, stack, &StreetConfig::srp_river());
    let ts = tree_stats(&tree);
    eprintln!(
        "tree: {} nodes ({} action, {} fold, {} showdown), ~{:.1} MB tables",
        ts.total_nodes, ts.action_nodes, ts.fold_terminals, ts.showdown_terminals,
        ts.memory_estimate_bytes as f64 / 1e6
    );

    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut solver = VectorRiverSolver::new(tree, board, ranges, variant);

    let start = Instant::now();
    let chunk = (iterations / 10).max(1);
    let mut done = 0;
    while done < iterations {
        let n = chunk.min(iterations - done);
        solver.run(n);
        done += n;
        eprintln!("iter {done}/{iterations}  elapsed {:.1}s", start.elapsed().as_secs_f64());
    }
    let expl = solver.exploitability_bb();
    let elapsed = start.elapsed().as_secs_f64();

    let root = solver.aggregate_strategy(0);
    println!("\n== solve-hu-river (abstract HU NLHE equilibrium solver) ==");
    println!("board {board_raw}  pot {pot_bb}bb  stack {stack_bb}bb  iters {iterations}");
    println!("exploitability: {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
        expl.exploitability, expl.br_value[0], expl.br_value[1]);
    println!("OOP (BB) root strategy:");
    for (action, freq) in &root {
        println!("  {action:<14} {:>6.2}%", freq * 100.0);
    }

    let out = out_dir.unwrap_or_else(|| {
        PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
            .join("projects/_data/gto/hu")
            .join(format!("river_{board_raw}"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");
    let stats = SolverStats {
        iterations,
        elapsed_secs: elapsed,
        expl,
        root_strategy: root,
    };
    write_strategy_csv(&out.join("strategy.csv"), &solver).expect("write csv");
    write_summary_json(&out.join("summary.json"), &board, &stats, &ts).expect("write json");
    eprintln!("wrote {}", out.display());
}
```

- [ ] **Step 2: Run the CLI end-to-end (real entry point check)**

```bash
cd ~/projects/gto
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 2000
```

Expected: progress lines, then a strategy table and an exploitability line
(< ~0.3 bb at 2000 iters; it keeps falling with more iterations), and
`strategy.csv` / `summary.json` under `~/projects/_data/gto/hu/river_AhKd7s2c9h/`.
Verify the files exist and quote the exploitability line in the report.

- [ ] **Step 3: Run the complete test suite (workspace)**

```bash
cd ~/projects/gto
cargo test -p gto-core && cargo test -p gto-hu --release
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): solve-hu-river CLI with exploitability report and CSV/JSON export"
```

---

### Task 6: Project docs

**Files:**
- Create: `gto/crates/gto-hu/README.md`
- Modify: `gto/README.md` (one line in the stack section)
- Modify: `gto/CLAUDE.md` (architecture table row + run command)

- [ ] **Step 1: Write `gto/crates/gto-hu/README.md`**

```markdown
# gto-hu — Abstract HU NLHE Equilibrium Solver

**This is an abstract HU NLHE equilibrium solver, not an unabstracted full
GTO solver.** Fixed action abstraction; exploitability (bb/hand) is always
reported alongside strategies.

Current scope (Phase 2): exact-combo river solver.

- Game: HU NLHE cash, configurable pot/stack, SRP river action set
  (check / bet 75% / bet 150% / all-in; vs bet: fold / call / raise-jam)
- Solver: CFR+ (default) or DCFR, per-combo vector traversal,
  blocker-exact showdowns
- Validation: Kuhn & Leduc on the same engine family, exact best response,
  scalar-vs-vector differential tests

## Usage

​```bash
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000
​```

Outputs an aggregate strategy table, exploitability in bb/hand, and
`strategy.csv` / `summary.json` under `~/projects/_data/gto/hu/`.

## Roadmap

Turn+river (public chance sampling) → flop trees → preflop with limp →
full blueprint. See `gto/docs/superpowers/specs/2026-06-06-hu-abstract-solver-design.md`.
​```

(Remove the zero-width escapes around the code fences when writing the
actual file — they exist only to nest fences in this plan.)

- [ ] **Step 2: Update `gto/README.md` and `gto/CLAUDE.md`**

In `gto/README.md` solver stack block, add one line under `gto-py`:

```
            └─ gto-hu    HU NLHE abstract equilibrium solver (CPU, exact BR)
```

In `gto/CLAUDE.md` architecture table, add:

```
| HU solver | `crates/gto-hu/` | Abstract HU NLHE equilibrium solver: river vector CFR+, Kuhn/Leduc validation, exact best response. CLI: `solve-hu-river` |
```

And in the Gotchas section append:

```
- **gto-hu is the only solver allowed to claim equilibrium output**, and
  only with its exploitability number attached. gto-core/gto-cuda remain
  single-street approximations (river-only correctness).
```

- [ ] **Step 3: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu/README.md gto/README.md gto/CLAUDE.md
git commit -m "docs(gto): document gto-hu river solver and demote legacy solvers in guides"
```

---

## Completion criteria for Phase 2b (= user acceptance for Phases 1+2)

1. `cargo test -p gto-core` and `cargo test -p gto-hu --release` fully green
2. Kuhn/Leduc pass on the production scalar engine (2a)
3. Differential tests: scalar ≡ vector on tiny spots (this plan, Task 3)
4. `solve-hu-river` runs end-to-end and reports exploitability in bb/hand
5. Average strategy (not latest) is what every export/getter returns
6. Tree stats + solver stats exported (CSV/JSON)
7. Docs state the abstract-solver disclaimer verbatim
