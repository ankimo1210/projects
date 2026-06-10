/// Multi-street GTO solver using Backward Induction + per-subgame DCFR.
///
/// Algorithm (PioSOLVER-style):
///   1. Solve every river subgame independently (2352 spots per flop)
///   2. Solve every turn subgame, using river EVs as terminal values
///   3. Solve the flop subgame, using turn EVs as terminal values
///
/// This avoids the O(49×48) full-enumeration explosion and allows each
/// level to be solved as independent batches on GPU.

use std::collections::HashMap;
use rayon::prelude::*;

use crate::range::{all_combos, Range, NUM_COMBOS};
use crate::tree::{GameTree, NodeKind, Street};

const ALPHA: f64 = 1.5;
const BETA:  f64 = 0.0;
const GAMMA: f64 = 2.0; // DCFR average-strategy discount exponent (Brown & Sandholm 2019)

// ---------------------------------------------------------------------------
// Single-street subgame CFR
// Supports optional external terminal EV table at NextStreet nodes.
// ---------------------------------------------------------------------------

pub struct SubgameSolver {
    pub tree:         GameTree,
    /// Board cards known at this street (3 = flop, 4 = turn, 5 = river).
    pub board:        Vec<u8>,
    /// Starting ranges (post card-removal for this board).
    pub ranges:       [Range; 2],
    /// Per (node, combo, action) cumulative regrets.
    regrets:          Vec<Vec<Vec<f64>>>,
    /// Per (node, combo, action) cumulative strategy sums.
    strategy_sum:     Vec<Vec<Vec<f64>>>,
    /// External EV tables at NextStreet nodes: node_id → [NUM_COMBOS] EV for player 0.
    pub next_evs:     HashMap<usize, Vec<f64>>,
    /// Per-combo showdown strengths (cached once at construction; board never changes).
    strengths:        Vec<u16>,
    /// All (card_a, card_b) combos, cached to avoid reallocating per showdown leaf.
    combos:           Vec<(u8, u8)>,
}

impl SubgameSolver {
    pub fn new(pot: i64, stack: i64, board: Vec<u8>, ranges: [Range; 2], street: Street) -> Self {
        let tree = GameTree::build(pot, stack, street);
        let regrets = tree.nodes.iter()
            .map(|nd| vec![vec![0.0f64; nd.children.len().max(1)]; NUM_COMBOS])
            .collect();
        let strategy_sum = tree.nodes.iter()
            .map(|nd| vec![vec![0.0f64; nd.children.len().max(1)]; NUM_COMBOS])
            .collect();
        let mut ranges = ranges;
        for r in &mut ranges { r.remove_blockers(&board); }
        let strengths = crate::eval::showdown_strengths(&board);
        let combos = all_combos();
        SubgameSolver { tree, board, ranges, regrets, strategy_sum, next_evs: HashMap::new(), strengths, combos }
    }

    pub fn run(&mut self, iterations: u32) -> f64 {
        for t in 1..=iterations {
            let aw = discount(t, ALPHA);
            let bw = discount(t, BETA);
            let sd = strategy_discount(t);
            for player in 0..2u8 {
                // reach = traverser's range, opp_reach = opponent's. Bind by
                // player so asymmetric ranges work (was ranges[0]/ranges[1] for both).
                let r_self = self.ranges[player as usize].weights;
                let r_opp  = self.ranges[1 - player as usize].weights;
                self.traverse(0, player, &r_self, &r_opp, aw, bw, sd);
            }
        }
        self.exploitability()
    }

    fn traverse(
        &mut self,
        node_id: usize,
        traverser: u8,
        reach: &[f64; NUM_COMBOS],
        opp_reach: &[f64; NUM_COMBOS],
        aw: f64, bw: f64, sd: f64,
    ) -> Vec<f64> {
        let node = self.tree.nodes[node_id].clone();

        match &node.kind {
            NodeKind::FoldTerminal { winner } => {
                let winner = *winner;
                let pot = node.pot as f64;
                let mut vals = vec![0.0f64; NUM_COMBOS];
                for i in 0..NUM_COMBOS {
                    if opp_reach[i] == 0.0 { continue; }
                    vals[i] = if winner == traverser { pot / 2.0 } else { -(pot / 2.0) };
                }
                vals
            }

            NodeKind::Showdown => {
                self.showdown_values(traverser, node.pot as f64, opp_reach)
            }

            NodeKind::NextStreet => {
                // Use externally-provided EV table (set by MultiStreetSolver).
                // EVs are from player-0 perspective; flip sign for player 1.
                if let Some(evs) = self.next_evs.get(&node_id) {
                    let evs = evs.clone();
                    let scale = if traverser == 0 { 1.0f64 } else { -1.0f64 };
                    evs.iter().map(|&v| v * scale).collect()
                } else {
                    // Fallback: treat as showdown (for unit tests without full pipeline)
                    self.showdown_values(traverser, node.pot as f64, opp_reach)
                }
            }

            NodeKind::Action { actor } => {
                let actor = *actor;
                let na = self.tree.nodes[node_id].children.len();
                if na == 0 { return vec![0.0; NUM_COMBOS]; }

                // Per-combo strategy via regret-matching+
                let strat: Vec<Vec<f64>> = (0..NUM_COMBOS)
                    .map(|c| self.current_strategy(node_id, c))
                    .collect();

                if actor == traverser {
                    let mut action_vals: Vec<Vec<f64>> = Vec::with_capacity(na);
                    for ai in 0..na {
                        let child_id = self.tree.nodes[node_id].children[ai].1;
                        let mut nr = *reach;
                        for c in 0..NUM_COMBOS { nr[c] *= strat[c][ai]; }
                        action_vals.push(self.traverse(child_id, traverser, &nr, opp_reach, aw, bw, sd));
                    }

                    // EV[c] = Σ_a σ(c, a) × action_vals[a][c]
                    let mut ev = vec![0.0f64; NUM_COMBOS];
                    for c in 0..NUM_COMBOS {
                        for ai in 0..na { ev[c] += strat[c][ai] * action_vals[ai][c]; }
                    }

                    // Per-(combo, action) regret update, discount applied once per iter
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
                    // Opponent's node: weight by per-combo σ, update strategy_sum
                    let mut ev = vec![0.0f64; NUM_COMBOS];
                    for ai in 0..na {
                        let child_id = self.tree.nodes[node_id].children[ai].1;
                        let mut nor = *opp_reach;
                        for c in 0..NUM_COMBOS {
                            // DCFR γ-discount on the average strategy (discount-then-add;
                            // each (node,c,ai) cell is touched once per iteration).
                            let s = &mut self.strategy_sum[node_id][c][ai];
                            *s = *s * sd + strat[c][ai] * reach[c];
                            nor[c] *= strat[c][ai];
                        }
                        let cv = self.traverse(child_id, traverser, reach, &nor, aw, bw, sd);
                        for c in 0..NUM_COMBOS { ev[c] += strat[c][ai] * cv[c]; }
                    }
                    ev
                }
            }
        }
    }

    fn current_strategy(&self, node_id: usize, combo: usize) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        if na == 0 { return vec![1.0]; }
        let reg = &self.regrets[node_id][combo];
        let pos_sum: f64 = reg.iter().take(na).map(|r| r.max(0.0)).sum();
        if pos_sum > 0.0 {
            reg.iter().take(na).map(|r| r.max(0.0) / pos_sum).collect()
        } else {
            vec![1.0 / na as f64; na]
        }
    }

    fn showdown_values(&self, traverser: u8, pot: f64, opp_reach: &[f64; NUM_COMBOS]) -> Vec<f64> {
        let combos = &self.combos;
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
                ev  += (if hs > os { half_pot } else if os > hs { -half_pot } else { 0.0 }) * ow;
                tot += ow;
            }
            (ci, if tot > 0.0 { ev / tot } else { 0.0 })
        }).collect();

        let mut vals = vec![0.0f64; NUM_COMBOS];
        for (ci, v) in results { vals[ci] = v; }
        vals
    }

    // -----------------------------------------------------------------------
    // Strategy / EV extraction
    // -----------------------------------------------------------------------

    pub fn root_strategy(&self) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[0];
        let na   = node.children.len();
        if na == 0 { return Vec::new(); }
        let mut avg = vec![0.0f64; na]; let mut total = 0.0;
        for c in 0..NUM_COMBOS {
            let w = self.ranges[0].weights[c]; if w == 0.0 { continue; }
            let sum: f64 = self.strategy_sum[0][c].iter().sum();
            for ai in 0..na {
                avg[ai] += (if sum > 0.0 { self.strategy_sum[0][c][ai] / sum } else { 1.0 / na as f64 }) * w;
            }
            total += w;
        }
        if total > 0.0 { for a in &mut avg { *a /= total; } }
        node.children.iter().zip(avg.iter())
            .map(|((act, _), &freq)| (format!("{act:?}"), freq))
            .collect()
    }

    /// Compute root EV (for player 0) averaged over range.
    pub fn root_ev(&mut self) -> Vec<f64> {
        let r0 = self.ranges[0].weights;
        let r1 = self.ranges[1].weights;
        // sd = 1.0: this is a read-only EV pass (strategy_sum is not consumed
        // afterwards for solvers on which root_ev is called).
        self.traverse(0, 0, &r0, &r1, 1.0, 1.0, 1.0)
    }

    /// Indices of all NextStreet nodes in the tree.
    pub fn next_street_node_ids(&self) -> Vec<usize> {
        self.tree.nodes.iter().enumerate()
            .filter(|(_, n)| n.kind == NodeKind::NextStreet)
            .map(|(i, _)| i)
            .collect()
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
}

// ---------------------------------------------------------------------------
// MultiStreetSolver: backward induction orchestrator
// ---------------------------------------------------------------------------

pub struct MultiStreetResult {
    pub flop_strategy:  Vec<(String, f64)>,
    pub exploitability: f64,
}

pub fn solve_multistreet(
    pot_bb: f64,
    effective_stack_bb: f64,
    flop_board: &[u8],   // 3 card indices
    iterations: u32,
) -> MultiStreetResult {
    let pot   = (pot_bb   * 100.0) as i64;
    let stack = (effective_stack_bb * 100.0) as i64;
    let ranges = [Range::new_uniform(), Range::new_uniform()];

    // -----------------------------------------------------------------------
    // Step 1: Solve flop to get NextStreet node pot/stacks
    // -----------------------------------------------------------------------
    let mut flop_solver = SubgameSolver::new(
        pot, stack, flop_board.to_vec(), ranges.clone(), Street::Flop,
    );

    // We need one warmup pass to find NextStreet node parameters
    let flop_ns_ids = flop_solver.next_street_node_ids();

    // Collect (node_id, pot, stacks) for each NextStreet on flop
    let flop_ns_params: Vec<(usize, i64, [i64; 2])> = flop_ns_ids.iter().map(|&nid| {
        let n = &flop_solver.tree.nodes[nid];
        (nid, n.pot, n.stacks)
    }).collect();

    // -----------------------------------------------------------------------
    // Step 2: For each (flop_ns, turn_card): solve turn, get turn EVs
    // -----------------------------------------------------------------------
    let valid_turns: Vec<u8> = (0u8..52).filter(|c| !flop_board.contains(c)).collect();

    // turn_evs[flop_ns_id][turn_card_idx] = Vec<f64> EV per combo (player 0 perspective)
    let mut flop_ns_evs: HashMap<usize, Vec<f64>> = HashMap::new();

    for &(fns_id, t_pot, t_stacks) in &flop_ns_params {
        let t_stack = t_stacks[0].min(t_stacks[1]);
        // Average turn EVs over consistent turn cards (per-combo denominator; a
        // flop-live combo is consistent with exactly n_turns - 2 of them).
        let mut turn_avg = ChanceAverager::new();

        for &tc in &valid_turns {
            let mut board4 = flop_board.to_vec();
            board4.push(tc);

            // Mask turn card from ranges
            let mut turn_ranges = ranges.clone();
            for r in &mut turn_ranges { r.remove_blockers(&board4); }

            let mut turn_solver = SubgameSolver::new(
                t_pot, t_stack, board4.clone(), turn_ranges, Street::Turn,
            );

            // Step 2a: For each (turn_ns, river_card): solve river
            let turn_ns_ids = turn_solver.next_street_node_ids();
            let turn_ns_params: Vec<(usize, i64, [i64; 2])> = turn_ns_ids.iter().map(|&nid| {
                let n = &turn_solver.tree.nodes[nid];
                (nid, n.pot, n.stacks)
            }).collect();

            let valid_rivers: Vec<u8> = (0u8..52).filter(|c| !board4.contains(c)).collect();

            for &(tns_id, r_pot, r_stacks) in &turn_ns_params {
                let r_stack = r_stacks[0].min(r_stacks[1]);
                // Average river EVs over consistent river cards. A river rc that
                // hits a hole card of combo i masks i out of river_ranges, so
                // river_ev[i] == 0 there; the mask excludes those so we divide by
                // the live count (n_rivers - 2 for a turn-live combo), not the full
                // candidate count which would scale live EVs by ~46/48.
                let mut river_avg = ChanceAverager::new();

                for &rc in &valid_rivers {
                    let mut board5 = board4.clone();
                    board5.push(rc);
                    let rc_mask = mask_card_arr(rc);
                    let mut river_ranges = ranges.clone();
                    for r in &mut river_ranges { r.remove_blockers(&board5); }

                    let mut river_solver = SubgameSolver::new(
                        r_pot, r_stack, board5, river_ranges, Street::River,
                    );
                    river_solver.run(iterations);
                    let river_ev = river_solver.root_ev();
                    river_avg.add(&river_ev, &rc_mask);
                }
                turn_solver.next_evs.insert(tns_id, river_avg.finish());
            }

            // Step 2b: Solve turn with river EVs
            turn_solver.run(iterations);
            let turn_ev = turn_solver.root_ev();

            // Accumulate (average over turn cards). Only turns consistent with
            // the combo contribute (mask), and the per-combo denominator divides
            // by that live count, not the full turn-candidate count.
            let tc_mask = mask_card_arr(tc);
            turn_avg.add(&turn_ev, &tc_mask);
        }
        flop_ns_evs.insert(fns_id, turn_avg.finish());
    }

    // -----------------------------------------------------------------------
    // Step 3: Solve flop with turn EVs
    // -----------------------------------------------------------------------
    for (fns_id, ev) in flop_ns_evs {
        flop_solver.next_evs.insert(fns_id, ev);
    }
    let expl = flop_solver.run(iterations);
    let strat = flop_solver.root_strategy();

    MultiStreetResult { flop_strategy: strat, exploitability: expl }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Returns a mask: true if combo i does NOT contain `card` (i.e. valid after card is dealt).
fn mask_card_arr(card: u8) -> [bool; NUM_COMBOS] {
    let combos = all_combos();
    let mut m = [true; NUM_COMBOS];
    for (i, &(ca, cb)) in combos.iter().enumerate() {
        if ca == card || cb == card { m[i] = false; }
    }
    m
}

/// Per-combo chance averaging over dealt cards.
///
/// Each contribution is masked: a combo is only consistent with the cards that
/// do not collide with its hole cards. Averaging must divide by the *per-combo*
/// number of consistent cards, not the full candidate count — otherwise live
/// continuation EVs are systematically scaled down (e.g. ~46/48 on the river,
/// ~47/49 on the turn) because 2 of the candidates always block any given combo.
struct ChanceAverager {
    sum:   Vec<f64>,
    count: Vec<u32>,
}

impl ChanceAverager {
    fn new() -> Self {
        ChanceAverager { sum: vec![0.0; NUM_COMBOS], count: vec![0; NUM_COMBOS] }
    }

    /// Add one card's per-combo EVs; `mask[i]` is true when combo i is consistent
    /// with that card (i.e. the card is not one of combo i's hole cards).
    fn add(&mut self, vals: &[f64], mask: &[bool; NUM_COMBOS]) {
        for i in 0..NUM_COMBOS {
            if mask[i] {
                self.sum[i] += vals[i];
                self.count[i] += 1;
            }
        }
    }

    /// Finalize to the per-combo mean (0 where no consistent card contributed).
    fn finish(self) -> Vec<f64> {
        let mut out = self.sum;
        for i in 0..NUM_COMBOS {
            if self.count[i] > 0 { out[i] /= self.count[i] as f64; }
        }
        out
    }
}

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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::eval::parse_card;

    fn board(cards: &[&str]) -> Vec<u8> {
        cards.iter().filter_map(|s| parse_card(s)).collect()
    }

    #[test]
    fn river_subgame_smoke() {
        let b = board(&["Kh", "7d", "2c", "As", "Jd"]);
        let ranges = [Range::new_uniform(), Range::new_uniform()];
        let mut s = SubgameSolver::new(650, 9700, b, ranges, Street::River);
        let expl = s.run(50);
        let strat = s.root_strategy();
        println!("River 50 iters: expl={expl:.4}, strategy={strat:?}");
        assert!(!strat.is_empty());
        assert!(expl.is_finite());
    }

    // B5: chance averaging must divide by the per-combo live count, not the full
    // candidate count. If every child EV equals a constant v for all live combos,
    // the parent (averaged) EV must equal v — not (live/total)·v.
    #[test]
    fn chance_average_constant_child_is_constant_parent() {
        // Use a 3-card "board" so each card masks out the combos containing it,
        // exactly as turn/river cards do in the real pipeline.
        let board_cards: [u8; 3] = [0, 1, 2];
        let candidates: Vec<u8> = (0u8..52).filter(|c| !board_cards.contains(c)).collect();
        let n = candidates.len(); // 49 (mirrors n_turns)
        assert_eq!(n, 49);

        const V: f64 = 7.0;
        let mut avg = ChanceAverager::new();
        for &card in &candidates {
            // Child EVs: constant V for combos consistent with `card`; the combos
            // that contain `card` are masked out, exactly what the real pipeline
            // does (those combos are removed from the per-card range).
            let mask = mask_card_arr(card);
            let vals = vec![V; NUM_COMBOS];
            avg.add(&vals, &mask);
        }
        let parent = avg.finish();

        // For a combo whose hole cards are both off the board, exactly 2 of the 49
        // candidates collide (one per hole card), so live count == 47 and the mean
        // must be exactly V. The buggy "divide by 49" would give 47/49·V instead.
        let combos = all_combos();
        let live_idx = combos.iter().position(|&(a, b)| a >= 3 && b >= 3).unwrap();
        assert!(
            (parent[live_idx] - V).abs() < 1e-12,
            "expected constant parent EV {V}, got {} (buggy 47/49·V = {})",
            parent[live_idx],
            47.0 / 49.0 * V,
        );

        // Spot-check the per-combo denominator equals the live count, not n.
        // Reconstruct the count for `live_idx`: it is masked only by the 2
        // candidates equal to its own hole cards.
        let (la, lb) = combos[live_idx];
        let live_count = candidates.iter()
            .filter(|&&card| card != la && card != lb)
            .count();
        assert_eq!(live_count, 47, "off-board combo must be consistent with 47 of 49 candidates");
    }

    #[test]
    fn flop_with_dummy_turn_ev() {
        let b = board(&["Kh", "7d", "2c"]);
        let ranges = [Range::new_uniform(), Range::new_uniform()];
        let mut s = SubgameSolver::new(650, 9700, b, ranges, Street::Flop);
        // Inject zero EV at NextStreet nodes (dummy)
        for nid in s.next_street_node_ids() {
            s.next_evs.insert(nid, vec![0.0; NUM_COMBOS]);
        }
        let expl = s.run(50);
        let strat = s.root_strategy();
        println!("Flop+dummy 50 iters: expl={expl:.4}, strategy={strat:?}");
        assert!(!strat.is_empty());
    }
}
