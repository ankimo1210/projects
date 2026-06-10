use super::regret::regret_matching;
use super::showdown::{weighted_compat, ShowdownTable};
use super::variant::CfrVariant;
use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::ranges::{all_combos, Range, NUM_COMBOS};
use crate::tree::{NodeKind, Tree};

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
    showdown: ShowdownTable,
    iteration: u32,
    /// All 1326 (card_a, card_b) pairs in combo-index order, cached once.
    combos: Vec<(u8, u8)>,
}

impl VectorRiverSolver {
    pub fn new(tree: Tree, board: [u8; 5], mut ranges: [Range; 2], variant: CfrVariant) -> Self {
        for r in &mut ranges {
            r.remove_blockers(&board);
        }
        let showdown = ShowdownTable::new(&board);
        let alloc = |tree: &Tree| -> Vec<Vec<f64>> {
            tree.nodes
                .iter()
                .map(|n| vec![0.0; n.children.len().max(1) * N])
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        let combos = all_combos();
        VectorRiverSolver {
            tree,
            board,
            ranges,
            variant,
            regrets,
            strat_sum,
            showdown,
            iteration: 0,
            combos,
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
                let compat = weighted_compat(&self.combos, opp_reach);
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
            NodeKind::Chance { .. } => unreachable!("river-only tree has no chance nodes"),
            NodeKind::NextStreet { .. } => unreachable!("river-only trees have no NextStreet nodes"),
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
                    // No per-combo skip here: regrets must keep updating even
                    // for own-reach-zero combos (their counterfactual signal
                    // is independent of own reach), and DCFR's per-iteration
                    // discounts must hit every combo every iteration.
                    let t = self.iteration;
                    let (sd, sw) = (
                        self.variant.strategy_discount(t),
                        self.variant.strategy_weight(t),
                    );
                    // Only two regret-discount factors exist for a fixed t
                    // (selected by the sign of the stored regret); hoist the
                    // two `powf`s out of the (combo, action) loop (I1).
                    let (d_pos, d_neg) = self.variant.regret_discounts(t);
                    let variant = self.variant;
                    let reg = &mut self.regrets[node_id];
                    let ssum = &mut self.strat_sum[node_id];
                    #[allow(clippy::needless_range_loop)]
                    for c in 0..N {
                        for a in 0..na {
                            let i = a * N + c;
                            let d = if reg[i] >= 0.0 { d_pos } else { d_neg };
                            let discounted = reg[i] * d;
                            reg[i] =
                                variant.accumulate_regret(discounted, action_vals[a][c] - ev[c]);
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
        self.showdown.diff(&self.combos, opp_reach)
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
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(br_player))[br_player as usize] as f64 / 100.0;
                self.showdown_diff(opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { .. } => unreachable!("river-only tree has no chance nodes"),
            NodeKind::NextStreet { .. } => unreachable!("river-only trees have no NextStreet nodes"),
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

    /// Counterfactual values for `player` when BOTH players follow the
    /// average strategy.  Mirrors `br_values` but uses the actor's average
    /// strategy (weighted sum) rather than the best response (max).
    ///
    /// Convention (same as `br_values` / `traverse`):
    ///   `opp_reach[c]` = reach of the opponent of `player`.
    ///   When `actor == player`: `player` follows avg strat → weight child
    ///     values by `avg_strat[a]` per combo; `opp_reach` is unchanged.
    ///   When `actor != player`: opponent follows avg strat → update
    ///     `opp_reach[c] *= opp_avg_strat(node, c)[a]` before recursing.
    fn avg_values(&self, node_id: usize, player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        let kind = self.tree.nodes[node_id].kind;
        match kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[player as usize] as f64 / 100.0;
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb = showdown_payoffs(&state, Some(player))[player as usize] as f64 / 100.0;
                self.showdown_diff(opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { .. } => unreachable!("river-only tree has no chance nodes"),
            NodeKind::NextStreet { .. } => unreachable!("river-only trees have no NextStreet nodes"),
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let mut ev = vec![0.0; N];
                if actor == player {
                    // Player follows avg strategy: weight child values by
                    // avg_strat[a] per combo; opp_reach is unchanged.
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.avg_values(child, player, opp_reach);
                        for c in 0..N {
                            let s = self.average_strategy(node_id, c);
                            ev[c] += s[a] * v[c];
                        }
                    }
                } else {
                    // Opponent follows avg strategy: update opp_reach by
                    // opponent's avg strat probability for each action.
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            let s = self.average_strategy(node_id, c);
                            no[c] = opp_reach[c] * s[a];
                        }
                        let v = self.avg_values(child, player, &no);
                        for c in 0..N {
                            ev[c] += v[c];
                        }
                    }
                }
                ev
            }
        }
    }

    /// Game value (bb/hand) to player 0 when both players follow the
    /// converged average strategy.  Intended for test / validation use.
    ///
    /// Normalization mirrors `exploitability_bb`:
    ///   value = Σ_c r0[c]·v0[c]  /  Σ_c r0[c]·compat(r1)[c]
    /// where v0 are counterfactual avg-vs-avg values for player 0.
    pub fn game_value_p0(&self) -> f64 {
        let r0 = self.ranges[0].weights;
        let r1 = self.ranges[1].weights;
        let vals = self.avg_values(0, 0, &r1);
        let compat = weighted_compat(&self.combos, &r1);
        let mut num = 0.0;
        let mut z = 0.0;
        for c in 0..N {
            if r0[c] > 0.0 {
                num += r0[c] * vals[c];
                z += r0[c] * compat[c];
            }
        }
        if z > 0.0 {
            num / z
        } else {
            0.0
        }
    }

    /// Exploitability in bb/hand: (BR_sb + BR_bb) / 2.
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
        ExplReport {
            br_value,
            exploitability: (br_value[0] + br_value[1]) / 2.0,
        }
    }
}
