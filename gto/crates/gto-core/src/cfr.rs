//! # ⚠ Single-street approximation — river-only correctness
//!
//! `CfrSolver` evaluates `NextStreet` nodes as immediate showdowns
//! (see the `NodeKind::Showdown | NodeKind::NextStreet` arm below).
//! Results are only game-theoretically meaningful on **river** (5-card)
//! boards. For flop/turn boards this is a rough approximation that
//! ignores future streets — never present its output as GTO.
//! The preflop-to-river solver lives in the `gto-hu` crate.
//!
//! Discounted CFR (DCFR) — corrected per-combo implementation.
//!
//! Algorithm (Brown & Sandholm 2019, External Sampling formulation):
//!   For each iteration t:
//!     For each player p:
//!       Recursive traverse:
//!         - At terminal: return per-combo value
//!         - At opponent's action node:
//!             For each action a:
//!               σ_opp(a|c) from per-combo regrets
//!               new_opp_reach[c] = opp_reach[c] × σ_opp(a|c)
//!               child_ev = traverse(child_a, ...)
//!               ev[c] += σ_opp(a|c) × child_ev[c]
//!               strategy_sum[node][c][a] += σ_opp(a|c) × reach[c]
//!         - At p's action node:
//!             Compute σ_p(a|c) from per-combo regrets
//!             For each action a:
//!               new_reach[c] = reach[c] × σ_p(a|c)
//!               action_vals[a] = traverse(child_a, ...)
//!             ev[c] = sum_a σ_p(a|c) × action_vals[a][c]
//!             For each combo c, action a:
//!               delta[c][a] = (action_vals[a][c] - ev[c]) × opp_reach[c]
//!               regrets[node][c][a] = (old × α or β) + delta[c][a]
//!
//! Key invariants:
//!   - Regrets are per (node, combo, action) — proper CFR
//!   - Discount applied ONCE per iteration via regret_update step
//!   - Strategy at any node is derived from per-combo regret-matching+

use crate::eval::Card;
use crate::range::{all_combos, Range, NUM_COMBOS};
use crate::tree::{GameTree, NodeKind};
use rayon::prelude::*;

const ALPHA: f64 = 1.5;
const BETA:  f64 = 0.0;
const GAMMA: f64 = 2.0; // DCFR average-strategy discount exponent (Brown & Sandholm 2019)

fn discount(t: u32, exp: f64) -> f64 {
    if exp == 0.0 { return 1.0; }
    let tf = t as f64;
    tf.powf(exp) / (tf.powf(exp) + 1.0)
}

/// DCFR γ-discount applied to the accumulated strategy sum each iteration:
/// (t/(t+1))^γ (mirrors gto-hu's `CfrVariant::strategy_discount`).
fn strategy_discount(t: u32) -> f64 {
    let tf = t as f64;
    (tf / (tf + 1.0)).powf(GAMMA)
}

pub struct CfrSolver {
    pub tree: GameTree,
    /// Per (node, combo, action) cumulative regrets.
    regrets:      Vec<Vec<Vec<f64>>>,
    /// Per (node, combo, action) cumulative strategy sums.
    strategy_sum: Vec<Vec<Vec<f64>>>,
    pub board:    Vec<Card>,
    pub ranges:   [Range; 2],
    /// Per-combo showdown strengths (cached once at construction; board never changes).
    strengths:    Vec<u16>,
    /// All (card_a, card_b) combos, cached to avoid reallocating per showdown leaf.
    combos:       Vec<(Card, Card)>,
}

impl CfrSolver {
    pub fn new(tree: GameTree, board: Vec<Card>, mut ranges: [Range; 2]) -> Self {
        for r in &mut ranges { r.remove_blockers(&board); }

        let regrets = tree.nodes.iter().map(|nd| {
            let na = nd.children.len().max(1);
            vec![vec![0.0f64; na]; NUM_COMBOS]
        }).collect();
        let strategy_sum = tree.nodes.iter().map(|nd| {
            let na = nd.children.len().max(1);
            vec![vec![0.0f64; na]; NUM_COMBOS]
        }).collect();
        let strengths = crate::eval::showdown_strengths(&board);
        let combos = all_combos();

        CfrSolver { tree, regrets, strategy_sum, board, ranges, strengths, combos }
    }

    /// Per-combo strategy at a node (regret-matching+).
    fn current_strategy(&self, node_id: usize, combo: usize) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        if na == 0 { return vec![1.0]; }
        let reg = &self.regrets[node_id][combo];
        let pos_sum: f64 = reg.iter().take(na).map(|&r| r.max(0.0)).sum();
        if pos_sum > 0.0 {
            reg.iter().take(na).map(|&r| r.max(0.0) / pos_sum).collect()
        } else {
            vec![1.0 / na as f64; na]
        }
    }

    pub fn run(&mut self, iterations: u32) -> f64 {
        for t in 1..=iterations {
            let aw = discount(t, ALPHA);
            let bw = discount(t, BETA);
            let sd = strategy_discount(t);
            for player in 0..2u8 {
                // traverse expects reach = traverser's range, opp_reach =
                // opponent's. Bind by player so asymmetric ranges are handled
                // correctly (was passing ranges[0]/ranges[1] for both players).
                let r_self = self.ranges[player as usize].weights;
                let r_opp  = self.ranges[1 - player as usize].weights;
                self.traverse(0, player, &r_self, &r_opp, aw, bw, sd);
            }
        }
        self.exploitability()
    }

    /// Test-only: reproduce the pre-fix (B11) binding, which passed
    /// ranges[0]/ranges[1] for BOTH traversers instead of binding by player.
    /// Used to demonstrate that the corrected binding changes behavior on
    /// asymmetric ranges.
    #[cfg(test)]
    fn run_legacy_binding(&mut self, iterations: u32) -> f64 {
        for t in 1..=iterations {
            let aw = discount(t, ALPHA);
            let bw = discount(t, BETA);
            let sd = strategy_discount(t);
            for player in 0..2u8 {
                let r0 = self.ranges[0].weights;
                let r1 = self.ranges[1].weights;
                self.traverse(0, player, &r0, &r1, aw, bw, sd);
            }
        }
        self.exploitability()
    }

    fn traverse(
        &mut self,
        node_id:   usize,
        traverser: u8,
        reach:     &[f64; NUM_COMBOS],
        opp_reach: &[f64; NUM_COMBOS],
        aw: f64, bw: f64, sd: f64,
    ) -> Vec<f64> {
        let node = self.tree.nodes[node_id].clone();

        match &node.kind {
            NodeKind::FoldTerminal { winner } => {
                let winner = *winner;
                let pot = node.pot as f64;
                let mut vals = vec![0.0f64; NUM_COMBOS];
                let val = if winner == traverser { pot / 2.0 } else { -(pot / 2.0) };
                for i in 0..NUM_COMBOS {
                    if opp_reach[i] == 0.0 { continue; }
                    vals[i] = val;
                }
                vals
            }

            NodeKind::Showdown | NodeKind::NextStreet => {
                // Single-street CFR treats NextStreet as Showdown approximation
                self.showdown_values(traverser, node.pot as f64, opp_reach)
            }

            NodeKind::Action { actor } => {
                let actor = *actor;
                let na    = node.children.len();
                if na == 0 { return vec![0.0; NUM_COMBOS]; }

                // Compute per-combo strategy for THIS node (used by both branches)
                let strat: Vec<Vec<f64>> = (0..NUM_COMBOS)
                    .map(|c| self.current_strategy(node_id, c))
                    .collect();

                if actor == traverser {
                    // Recurse for each action with updated reach (traverser's)
                    let mut action_vals: Vec<Vec<f64>> = Vec::with_capacity(na);
                    for ai in 0..na {
                        let child_id = node.children[ai].1;
                        let mut new_reach = *reach;
                        for c in 0..NUM_COMBOS { new_reach[c] *= strat[c][ai]; }
                        action_vals.push(self.traverse(child_id, traverser, &new_reach, opp_reach, aw, bw, sd));
                    }

                    // EV[c] = Σ_a σ(c, a) × action_vals[a][c]
                    let mut ev = vec![0.0f64; NUM_COMBOS];
                    for c in 0..NUM_COMBOS {
                        for ai in 0..na { ev[c] += strat[c][ai] * action_vals[ai][c]; }
                    }

                    // Regret update: per (combo, action), with discount per iteration (not per combo)
                    for c in 0..NUM_COMBOS {
                        if opp_reach[c] == 0.0 { continue; }
                        let ow = opp_reach[c];
                        for ai in 0..na {
                            let delta = (action_vals[ai][c] - ev[c]) * ow;
                            let r = &mut self.regrets[node_id][c][ai];
                            *r = if *r >= 0.0 { *r * aw + delta } else { *r * bw + delta };
                            *r = r.clamp(-1e9, 1e9);
                        }
                    }
                    ev
                } else {
                    // Opponent's node: weight EV by σ_opp, update strategy_sum
                    let mut ev = vec![0.0f64; NUM_COMBOS];
                    for ai in 0..na {
                        let child_id = node.children[ai].1;
                        let mut new_opp = *opp_reach;
                        for c in 0..NUM_COMBOS {
                            // Accumulate strategy sum at opponent's node with DCFR's
                            // γ-discount (discount-then-add: each (node,c,ai) cell is
                            // touched exactly once per iteration). Without sd the
                            // average strategy is undiscounted while regrets are not.
                            let s = &mut self.strategy_sum[node_id][c][ai];
                            *s = *s * sd + strat[c][ai] * reach[c];
                            new_opp[c] *= strat[c][ai];
                        }
                        let child_vals = self.traverse(child_id, traverser, reach, &new_opp, aw, bw, sd);
                        // Weight by opponent's per-combo strategy probability
                        for c in 0..NUM_COMBOS { ev[c] += strat[c][ai] * child_vals[c]; }
                    }
                    ev
                }
            }
        }
    }

    fn showdown_values(&self, traverser: u8, pot: f64, opp_reach: &[f64; NUM_COMBOS]) -> Vec<f64> {
        let combos   = &self.combos;
        let half_pot = pot / 2.0;

        let strengths = &self.strengths;

        let active_hero: Vec<(usize, u16)> = (0..NUM_COMBOS)
            .filter(|&i| self.ranges[traverser as usize].weights[i] > 0.0 && strengths[i] > 0)
            .map(|i| (i, strengths[i]))
            .collect();

        let active_opp: Vec<(usize, u16, f64)> = (0..NUM_COMBOS)
            .filter(|&i| opp_reach[i] > 0.0 && strengths[i] > 0)
            .map(|i| (i, strengths[i], opp_reach[i]))
            .collect();

        let results: Vec<(usize, f64)> = active_hero.par_iter().map(|&(ci, hs)| {
            let (ca, cb) = combos[ci];
            let mut ev = 0.0f64; let mut tot = 0.0f64;
            for &(oi, os, ow) in &active_opp {
                let (oa, ob) = combos[oi];
                if oa == ca || oa == cb || ob == ca || ob == cb { continue; }
                let outcome = if hs > os { half_pot } else if os > hs { -half_pot } else { 0.0 };
                ev  += outcome * ow;
                tot += ow;
            }
            (ci, if tot > 0.0 { ev / tot } else { 0.0 })
        }).collect();

        let mut vals = vec![0.0f64; NUM_COMBOS];
        for (ci, v) in results { vals[ci] = v; }
        vals
    }

    pub fn exploitability(&self) -> f64 {
        let mut total_pos: f64 = 0.0;
        let mut active = 0usize;
        for combo in 0..NUM_COMBOS {
            let pos: f64 = self.regrets[0][combo].iter().map(|&r| r.max(0.0)).sum();
            if pos > 0.0 { total_pos += pos; active += 1; }
        }
        if active == 0 { return 0.0; }
        total_pos / active as f64
    }

    /// Aggregate root strategy (averaged over initial range).
    pub fn root_strategy(&self) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[0];
        let na = node.children.len();
        if na == 0 { return Vec::new(); }
        let mut avg = vec![0.0f64; na];
        let mut total = 0.0f64;
        for c in 0..NUM_COMBOS {
            let w = self.ranges[0].weights[c];
            if w == 0.0 { continue; }
            let sum: f64 = self.strategy_sum[0][c].iter().sum();
            for ai in 0..na {
                let f = if sum > 0.0 { self.strategy_sum[0][c][ai] / sum } else { 1.0 / na as f64 };
                avg[ai] += f * w;
            }
            total += w;
        }
        if total > 0.0 { for a in &mut avg { *a /= total; } }
        node.children.iter().zip(avg.iter())
            .map(|((act, _), &freq)| (format!("{act:?}"), freq))
            .collect()
    }

    /// Per-combo strategies at root (for combo grid coloring).
    pub fn combo_strategies(&self) -> Vec<(usize, String, f64)> {
        let node = &self.tree.nodes[0];
        let na = node.children.len();
        if na == 0 { return Vec::new(); }
        let action_names: Vec<String> = node.children.iter()
            .map(|(act, _)| format!("{act:?}")).collect();

        let mut out = Vec::new();
        for c in 0..NUM_COMBOS {
            if self.ranges[0].weights[c] == 0.0 { continue; }
            let sum: f64 = self.strategy_sum[0][c].iter().sum();
            for ai in 0..na {
                let f = if sum > 0.0 {
                    self.strategy_sum[0][c][ai] / sum
                } else { 1.0 / na as f64 };
                if f > 0.001 {
                    out.push((c, action_names[ai].clone(), f));
                }
            }
        }
        out
    }

    /// Current regret-matching strategy at an arbitrary node, averaged over the
    /// given actor's range. Test-only: lets white-box tests inspect the realized
    /// strategy at non-root (e.g. IP) nodes. Reads regrets (not strategy_sum),
    /// which is what actually drives play and what B11 corrupts.
    #[cfg(test)]
    fn node_avg_current_strategy(&self, node_id: usize, actor: u8) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        if na == 0 { return Vec::new(); }
        let mut avg = vec![0.0f64; na];
        let mut total = 0.0f64;
        for c in 0..NUM_COMBOS {
            let w = self.ranges[actor as usize].weights[c];
            if w == 0.0 { continue; }
            let strat = self.current_strategy(node_id, c);
            for ai in 0..na {
                avg[ai] += strat[ai] * w;
            }
            total += w;
        }
        if total > 0.0 { for a in &mut avg { *a /= total; } }
        avg
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::eval::{parse_card, showdown_strengths};
    use crate::tree::{Action, Street};

    fn card(s: &str) -> Card { parse_card(s).unwrap() }

    fn cards(ss: &[&str]) -> Vec<Card> { ss.iter().map(|s| card(s)).collect() }

    /// Find the IP (player-1) node that arises after OOP bets at the root:
    /// root → (Bet) → player-1 Action node with a Fold child.
    fn ip_facing_bet_node(tree: &GameTree) -> usize {
        let (_, bet_child) = tree.nodes[0].children.iter()
            .find(|(a, _)| *a == Action::Bet)
            .expect("root must offer a Bet");
        let nid = *bet_child;
        assert!(matches!(tree.nodes[nid].kind, NodeKind::Action { actor: 1 }));
        nid
    }

    // -----------------------------------------------------------------------
    // B11: traverse must bind reach = traverser's range, opp_reach = opponent's.
    //
    // The corrected `run` binds the traverser's own range as `reach` and the
    // opponent's as `opp_reach`; the pre-fix code passed ranges[0]/ranges[1] for
    // BOTH traversers (reproduced here by `run_legacy_binding`). The two agree iff
    // r0 == r1, which is exactly why the bug was "currently harmless". With
    // ASYMMETRIC ranges they must diverge: player 1's regret update weights by the
    // wrong range under the legacy binding, so its strategy at the IP node detectably
    // differs. This test pins that the fixed binding changes behavior (fails to
    // diverge on the pre-fix code, where both `run` and `run_legacy_binding` are the
    // same buggy call).
    //
    // Ranges overlap on the "air" combos so the per-combo regret weight
    // opp_reach[c] is nonzero for IP under either binding (isolating B11 from the
    // unrelated own-range zero-weight skip).
    // -----------------------------------------------------------------------
    #[test]
    fn b11_correct_binding_differs_from_legacy_on_asymmetric_ranges() {
        let board = cards(&["Ah", "Kd", "Qc", "7s", "2h"]);
        let strengths = showdown_strengths(&board);

        let mut live: Vec<(usize, u16)> = (0..NUM_COMBOS)
            .filter(|&i| strengths[i] > 0)
            .map(|i| (i, strengths[i]))
            .collect();
        live.sort_by_key(|&(_, s)| s);
        assert!(live.len() > 40);

        let weak: Vec<usize> = live.iter().take(12).map(|&(ci, _)| ci).collect();
        let nut = live.last().unwrap().0;

        // OOP (player 0): polarized = nuts + weak air. IP (player 1): weak air only.
        let mut r0 = Range::new_empty();
        r0.weights[nut] = 1.0;
        for &ci in &weak { r0.weights[ci] = 1.0; }
        let mut r1 = Range::new_empty();
        for &ci in &weak { r1.weights[ci] = 1.0; }

        let tree = GameTree::build(200, 2000, Street::River);
        let ip_node = ip_facing_bet_node(&tree);

        let iters = 400;

        // Fixed (correct per-player) binding.
        let mut fixed = CfrSolver::new(
            GameTree::build(200, 2000, Street::River),
            board.clone(),
            [r0.clone(), r1.clone()],
        );
        fixed.run(iters);
        let strat_fixed = fixed.node_avg_current_strategy(ip_node, 1);

        // Legacy (pre-fix) binding on the same inputs.
        let mut legacy = CfrSolver::new(
            GameTree::build(200, 2000, Street::River),
            board.clone(),
            [r0, r1],
        );
        legacy.run_legacy_binding(iters);
        let strat_legacy = legacy.node_avg_current_strategy(ip_node, 1);

        let l1: f64 = strat_fixed.iter().zip(&strat_legacy)
            .map(|(a, b)| (a - b).abs()).sum();
        println!("B11 IP strat fixed={strat_fixed:?} legacy={strat_legacy:?} L1={l1:.4}");
        assert!(
            l1 > 0.1,
            "correct binding must yield a different IP strategy than the legacy \
             (B11) binding on asymmetric ranges; L1 diff = {l1:.4}"
        );

        // Sanity: with symmetric ranges the two bindings coincide (the bug is
        // harmless), confirming the divergence above is due to asymmetry.
        let sym = Range::new_uniform();
        let mut a = CfrSolver::new(
            GameTree::build(200, 2000, Street::River), board.clone(),
            [sym.clone(), sym.clone()],
        );
        a.run(iters);
        let mut b = CfrSolver::new(
            GameTree::build(200, 2000, Street::River), board,
            [sym.clone(), sym],
        );
        b.run_legacy_binding(iters);
        let sa = a.node_avg_current_strategy(ip_node, 1);
        let sb = b.node_avg_current_strategy(ip_node, 1);
        let l1_sym: f64 = sa.iter().zip(&sb).map(|(x, y)| (x - y).abs()).sum();
        assert!(l1_sym < 1e-9, "symmetric ranges: bindings must coincide; L1={l1_sym}");
    }

    // -----------------------------------------------------------------------
    // B8: DCFR γ-discount must be applied to the average strategy each iteration.
    //
    // At the root (player 0's node) strategy_sum is accumulated once per iteration
    // in the opponent branch (traverser = 1), with contribution strat[c][ai]·reach[c]
    // and reach = player 1's (uniform → 1.0) range. Summed over the node's actions
    // that contribution is exactly reach[c] = 1.0 per iteration, since the per-combo
    // strategy sums to 1 over actions. DCFR discounts the running sum by
    // sd_t = (t/(t+1))^γ (γ=2) before each add, so after N iterations the total
    // root strategy_sum mass for a live combo is the closed form
    //   S_N = Σ_{t=1}^{N} 1.0 · Π_{k=t+1}^{N} sd_k,
    // which is STRICTLY below the undiscounted N (the pre-fix behavior, where the
    // factor was bw.max(1.0) = 1.0 and the sum grew to exactly N).
    // -----------------------------------------------------------------------
    #[test]
    fn b8_strategy_sum_is_gamma_discounted() {
        let n = 5u32;

        // The discount factor must be (t/(t+1))^2 (γ=2), not 1.0.
        assert!((strategy_discount(1) - (0.5f64).powi(2)).abs() < 1e-12);
        assert!((strategy_discount(2) - (2.0f64 / 3.0).powi(2)).abs() < 1e-12);

        // Closed-form reference: discount-then-add of a constant 1.0 contribution.
        let mut s_ref = 0.0f64;
        for t in 1..=n {
            s_ref = s_ref * strategy_discount(t) + 1.0;
        }
        let undiscounted = n as f64; // pre-fix sum
        assert!(
            (s_ref - undiscounted).abs() > 1e-2,
            "discounted sum {s_ref} must differ from undiscounted {undiscounted}"
        );

        // Exercise the real solver and confirm the root strategy_sum mass matches
        // the discounted closed form (and is below the undiscounted bound).
        let board = cards(&["Ah", "Kd", "Qc", "7s", "2h"]);
        let ranges = [Range::new_uniform(), Range::new_uniform()];
        let tree = GameTree::build(200, 2000, Street::River);
        let mut solver = CfrSolver::new(tree, board, ranges);
        solver.run(n);

        let mut any_checked = false;
        for c in 0..NUM_COMBOS {
            if solver.ranges[1].weights[c] == 0.0 { continue; }
            let mass: f64 = solver.strategy_sum[0][c].iter().sum();
            if mass <= 0.0 { continue; }
            println!("B8 root combo {c}: mass={mass:.6}, discounted_ref={s_ref:.6}, undiscounted={undiscounted}");
            assert!(
                mass < undiscounted - 1e-6,
                "root strategy_sum mass {mass} must be < undiscounted {undiscounted} (γ-discount missing?)"
            );
            assert!(
                (mass - s_ref).abs() < 1e-9,
                "root strategy_sum mass {mass} should equal discounted closed form {s_ref}"
            );
            any_checked = true;
            break;
        }
        assert!(any_checked, "expected at least one live root combo");
    }
}
