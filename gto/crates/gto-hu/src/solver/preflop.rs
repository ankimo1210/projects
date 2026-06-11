//! Exact-combo vector CFR for the standalone HU preflop tree (Phase 5).
//! No chance nodes: `NextStreet` leaves pay all-in equity from the
//! injected `EquityTable` (the simplified postflop value model, spec
//! §13). Best response and exploitability are exact RELATIVE TO THAT
//! MODEL — strategies must not be quoted as full-game equilibria.

use super::equity_model::EquityTable;
use super::regret::regret_matching;
use super::showdown::weighted_compat;
use super::variant::CfrVariant;
use super::vector::ExplReport;
use crate::game::terminal::fold_payoffs;
use crate::game::{BettingState, Street};
use crate::ranges::{all_combos, Range, NUM_COMBOS};
use crate::tree::{NodeKind, Tree};

const N: usize = NUM_COMBOS;

pub struct PreflopSolver {
    pub tree: Tree,
    pub ranges: [Range; 2],
    pub variant: CfrVariant,
    eq: EquityTable,
    /// [node] → flat na*N tables (dense — the preflop tree is tiny).
    regrets: Vec<Vec<f64>>,
    strat_sum: Vec<Vec<f64>>,
    iteration: u32,
    combos: Vec<(u8, u8)>,
}

impl PreflopSolver {
    pub fn new(tree: Tree, ranges: [Range; 2], variant: CfrVariant, eq: EquityTable) -> Self {
        assert_eq!(
            tree.nodes[0].state.street,
            Street::Preflop,
            "root must be a preflop node (build with build_preflop_tree)"
        );
        let alloc = |tree: &Tree| -> Vec<Vec<f64>> {
            tree.nodes
                .iter()
                .map(|n| match n.kind {
                    NodeKind::Action { .. } => vec![0.0; n.children.len() * N],
                    _ => Vec::new(),
                })
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        PreflopSolver {
            tree,
            ranges,
            variant,
            eq,
            regrets,
            strat_sum,
            iteration: 0,
            combos: all_combos(),
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

    /// Equity-model payoff at a street-end leaf: per traverser combo c,
    /// Σ over compatible villain combos o of
    /// opp_reach[o] × (eq(c,o)·pot − contrib) in bb. O(N²) with blocker
    /// skips — the preflop tree only has a dozen such leaves.
    fn equity_values(
        &self,
        state: &BettingState,
        traverser: u8,
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let pot = state.pot() as f64;
        let contrib = state.contrib[traverser as usize] as f64;
        let mut out = vec![0.0; N];
        for (c, ev) in out.iter_mut().enumerate() {
            let (c0, c1) = self.combos[c];
            let mut v = 0.0;
            for o in 0..N {
                let w = opp_reach[o];
                if w == 0.0 {
                    continue;
                }
                let (o0, o1) = self.combos[o];
                if o0 == c0 || o0 == c1 || o1 == c0 || o1 == c1 {
                    continue;
                }
                v += w * (self.eq.eq(c, o) as f64 * pot - contrib);
            }
            *ev = v / 100.0; // centi-bb → bb
        }
        out
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
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::NextStreet { .. } => {
                let state = self.tree.nodes[node_id].state;
                self.equity_values(&state, traverser, opp_reach)
            }
            NodeKind::Showdown | NodeKind::Chance { .. } => {
                unreachable!("preflop trees have no showdown/chance nodes")
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
                    let (sd, sw) = (
                        self.variant.strategy_discount(t),
                        self.variant.strategy_weight(t),
                    );
                    let variant = self.variant;
                    let reg = &mut self.regrets[node_id];
                    let ssum = &mut self.strat_sum[node_id];
                    #[allow(clippy::needless_range_loop)]
                    for c in 0..N {
                        for a in 0..na {
                            let i = a * N + c;
                            let discounted = reg[i] * variant.regret_discount(reg[i], t);
                            reg[i] =
                                variant.accumulate_regret(discounted, action_vals[a][c] - ev[c]);
                            ssum[i] = ssum[i] * sd + sw * reach[c] * strat[a * N + c];
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

    /// Normalized average strategy for ALL combos: [action * N + combo].
    fn avg_matrix(&self, node_id: usize, na: usize) -> Vec<f64> {
        let ssum = &self.strat_sum[node_id];
        let mut strat = vec![1.0 / na as f64; na * N];
        for c in 0..N {
            let total: f64 = (0..na).map(|a| ssum[a * N + c]).sum();
            if total > 0.0 {
                for a in 0..na {
                    strat[a * N + c] = ssum[a * N + c] / total;
                }
            }
        }
        strat
    }

    /// Range-weighted aggregate strategy at a node for display.
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

    // ----- Exact best response (within the equity model) ----------------

    fn br_values(&self, node_id: usize, br_player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[br_player as usize] as f64 / 100.0;
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::NextStreet { .. } => {
                let state = self.tree.nodes[node_id].state;
                self.equity_values(&state, br_player, opp_reach)
            }
            NodeKind::Showdown | NodeKind::Chance { .. } => {
                unreachable!("preflop trees have no showdown/chance nodes")
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
                    let strat = self.avg_matrix(node_id, na);
                    let mut ev = vec![0.0; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] = opp_reach[c] * strat[a * N + c];
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

    /// Counterfactual values when BOTH players follow the average strategy.
    fn avg_values(&self, node_id: usize, player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[player as usize] as f64 / 100.0;
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::NextStreet { .. } => {
                let state = self.tree.nodes[node_id].state;
                self.equity_values(&state, player, opp_reach)
            }
            NodeKind::Showdown | NodeKind::Chance { .. } => {
                unreachable!("preflop trees have no showdown/chance nodes")
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let strat = self.avg_matrix(node_id, na);
                let mut ev = vec![0.0; N];
                if actor == player {
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.avg_values(child, player, opp_reach);
                        for c in 0..N {
                            ev[c] += strat[a * N + c] * v[c];
                        }
                    }
                } else {
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] = opp_reach[c] * strat[a * N + c];
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

    /// Game value (bb/hand) to player 0 (SB) under avg-vs-avg play,
    /// exact within the equity model.
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

    /// Exploitability in bb/hand within the equity model:
    /// (BR_sb + BR_bb) / 2.
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
        ExplReport::zero_sum(br_value)
    }
}
