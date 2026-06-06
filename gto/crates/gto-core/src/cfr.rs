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

fn discount(t: u32, exp: f64) -> f64 {
    if exp == 0.0 { return 1.0; }
    let tf = t as f64;
    tf.powf(exp) / (tf.powf(exp) + 1.0)
}

pub struct CfrSolver {
    pub tree: GameTree,
    /// Per (node, combo, action) cumulative regrets.
    regrets:      Vec<Vec<Vec<f64>>>,
    /// Per (node, combo, action) cumulative strategy sums.
    strategy_sum: Vec<Vec<Vec<f64>>>,
    pub board:    Vec<Card>,
    pub ranges:   [Range; 2],
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

        CfrSolver { tree, regrets, strategy_sum, board, ranges }
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
            for player in 0..2u8 {
                let r0 = self.ranges[0].weights;
                let r1 = self.ranges[1].weights;
                self.traverse(0, player, &r0, &r1, aw, bw);
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
        aw: f64, bw: f64,
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
                        action_vals.push(self.traverse(child_id, traverser, &new_reach, opp_reach, aw, bw));
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
                            // Accumulate strategy sum at opponent's node (DCFR β)
                            self.strategy_sum[node_id][c][ai] += strat[c][ai] * reach[c] * bw.max(1.0);
                            new_opp[c] *= strat[c][ai];
                        }
                        let child_vals = self.traverse(child_id, traverser, reach, &new_opp, aw, bw);
                        // Weight by opponent's per-combo strategy probability
                        for c in 0..NUM_COMBOS { ev[c] += strat[c][ai] * child_vals[c]; }
                    }
                    ev
                }
            }
        }
    }

    fn showdown_values(&self, traverser: u8, pot: f64, opp_reach: &[f64; NUM_COMBOS]) -> Vec<f64> {
        let combos   = all_combos();
        let half_pot = pot / 2.0;
        let board    = &self.board;

        let strengths: Vec<u16> = crate::eval::showdown_strengths(board);

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
}
