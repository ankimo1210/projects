//! Phase 6 blueprint: the composed HU game over an M-flop board
//! abstraction (design: 2026-06-08-blueprint-design.md, v2).
//!
//! Measure (design §3): the abstract game uses the JOINT measure
//!   μ(h, v, m) ∝ w0(h) · w1(v) · w_m · 1[legal(h,v,m)]
//! — hand deals occur proportionally to Z(h,v) = Σ_{legal m} w_m.
//! Postflop traversal stays O(N) per node (per-combo masks, exactly the
//! standalone FlopSolver); the entire correction lives here in the
//! preflop layer: FOLD terminals weight each pair by Z(c,o), all-in
//! leaves sum w_m-weighted exact runout equity over legal flops, and
//! the game-value / BR normalizers use Σ w0·w1·compat·Z.
//!
//! Claim discipline (design §3): outputs are a "CFR profile with exact
//! exploitability X bb/hand on the M-flop abstract game" — never an
//! equilibrium claim. Convergence under bucketed subgame storage is
//! empirical; the exact composed best response keeps the number honest.

use super::equity_model::flop_allin_equity;
use super::flop::{Abstraction, FlopSolver};
use super::regret::regret_matching;
use super::turn_river::ChanceMode;
use super::variant::CfrVariant;
use super::vector::ExplReport;
use crate::game::terminal::fold_payoffs;
use crate::game::{PotType, Street};
use crate::ranges::{all_combos, Range, NUM_COMBOS};
use crate::tree::{build_flop_tree, FlopTreeConfig, NodeKind, Tree};

const N: usize = NUM_COMBOS;

/// One non-all-in preflop leaf and its M flop subgames.
struct Leaf {
    /// Preflop tree node id (subgames are keyed by node id — the two
    /// (24, 88) limp-3bet lines stay separate, design §2).
    node_id: usize,
    subgames: Vec<FlopSolver>, // [m]
}

pub struct BlueprintSolver {
    pub preflop_tree: Tree,
    pub ranges: [Range; 2],
    pub variant: CfrVariant,
    flops: Vec<[u8; 3]>,
    /// Normalized flop weights w_m.
    weights: Vec<f64>,
    leaves: Vec<Leaf>,
    /// node id → index into `leaves` (usize::MAX = not a betting leaf).
    leaf_of: Vec<usize>,
    /// [m] exact all-in runout equity, N×N (hero-major).
    allin_eq: Vec<Vec<f32>>,
    /// Per combo: bit m set iff the combo blocks flop m.
    block_mask: Vec<u8>,
    /// zsum[mask] = Σ_{m ∉ mask} w_m  (so Z(c,o) = zsum[mask_c | mask_o]).
    zsum: Vec<f64>,
    /// Preflop tables: exact per-combo rows, [node] → na*N.
    regrets: Vec<Vec<f64>>,
    strat_sum: Vec<Vec<f64>>,
    iteration: u32,
    combos: Vec<(u8, u8)>,
}

fn config_for(pot_type: PotType) -> FlopTreeConfig {
    match pot_type {
        PotType::Limped | PotType::Srp => FlopTreeConfig::srp(),
        PotType::ThreeBet => FlopTreeConfig::threebet(),
        PotType::FourBet => FlopTreeConfig::fourbet(),
        PotType::AllInPreflop => unreachable!("all-in leaves have no betting subgame"),
    }
}

impl BlueprintSolver {
    /// `flops`/`weights`: the M sampled canonical flops (weights need not
    /// be normalized; they are here). Subgame chance mode: `Sample` uses
    /// per-subgame seeds derived from `seed`; `Enumerate` is exact.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        preflop_tree: Tree,
        ranges: [Range; 2],
        variant: CfrVariant,
        flops: Vec<[u8; 3]>,
        weights: Vec<f64>,
        abs: Abstraction,
        sample: bool,
        seed: u64,
    ) -> Self {
        Self::new_with_configs(
            preflop_tree,
            ranges,
            variant,
            flops,
            weights,
            abs,
            sample,
            seed,
            config_for,
        )
    }

    /// Like `new` but with injectable per-pot-type subgame configs
    /// (tests use tiny action sets to keep enumerated runs affordable).
    #[allow(clippy::too_many_arguments)]
    pub fn new_with_configs(
        preflop_tree: Tree,
        ranges: [Range; 2],
        variant: CfrVariant,
        flops: Vec<[u8; 3]>,
        weights: Vec<f64>,
        abs: Abstraction,
        sample: bool,
        seed: u64,
        config_fn: impl Fn(PotType) -> FlopTreeConfig,
    ) -> Self {
        assert_eq!(
            preflop_tree.nodes[0].state.street,
            Street::Preflop,
            "root must be a preflop tree"
        );
        let m_count = flops.len();
        assert!(m_count > 0 && m_count <= 8, "1..=8 flops supported");
        assert_eq!(weights.len(), m_count);
        let wsum: f64 = weights.iter().sum();
        assert!(wsum > 0.0, "weights must be positive");
        let weights: Vec<f64> = weights.iter().map(|w| w / wsum).collect();

        let combos = all_combos();
        let mut block_mask = vec![0u8; N];
        for (c, &(a, b)) in combos.iter().enumerate() {
            for (m, f) in flops.iter().enumerate() {
                if f.contains(&a) || f.contains(&b) {
                    block_mask[c] |= 1 << m;
                }
            }
        }
        let mut zsum = vec![0.0f64; 1 << m_count];
        for (mask, z) in zsum.iter_mut().enumerate() {
            *z = (0..m_count)
                .filter(|&m| mask & (1 << m) == 0)
                .map(|m| weights[m])
                .sum();
        }

        let allin_eq: Vec<Vec<f32>> = flops.iter().map(|&f| flop_allin_equity(f)).collect();

        // Betting subgames per non-all-in NextStreet leaf, keyed by node id.
        let mut leaves = Vec::new();
        let mut leaf_of = vec![usize::MAX; preflop_tree.nodes.len()];
        for (node_id, node) in preflop_tree.nodes.iter().enumerate() {
            if let NodeKind::NextStreet { pot_type } = node.kind {
                if pot_type == PotType::AllInPreflop {
                    continue;
                }
                let pot = node.state.pot();
                let stack = node.state.stacks[0];
                debug_assert_eq!(node.state.stacks[0], node.state.stacks[1]);
                let cfg = config_fn(pot_type);
                let subgames: Vec<FlopSolver> = flops
                    .iter()
                    .enumerate()
                    .map(|(m, &board)| {
                        let mode = if sample {
                            ChanceMode::Sample {
                                seed: seed ^ ((node_id as u64) << 8 | m as u64),
                            }
                        } else {
                            ChanceMode::Enumerate
                        };
                        FlopSolver::new_abstracted(
                            build_flop_tree(pot, stack, &cfg),
                            board,
                            ranges.clone(),
                            variant,
                            mode,
                            abs,
                        )
                    })
                    .collect();
                leaf_of[node_id] = leaves.len();
                leaves.push(Leaf { node_id, subgames });
            }
        }

        let alloc = |tree: &Tree| -> Vec<Vec<f64>> {
            tree.nodes
                .iter()
                .map(|n| match n.kind {
                    NodeKind::Action { .. } => vec![0.0; n.children.len() * N],
                    _ => Vec::new(),
                })
                .collect()
        };
        let regrets = alloc(&preflop_tree);
        let strat_sum = alloc(&preflop_tree);
        BlueprintSolver {
            preflop_tree,
            ranges,
            variant,
            flops,
            weights,
            leaves,
            leaf_of,
            allin_eq,
            block_mask,
            zsum,
            regrets,
            strat_sum,
            iteration: 0,
            combos,
        }
    }

    pub fn flops(&self) -> &[[u8; 3]] {
        &self.flops
    }

    pub fn weights(&self) -> &[f64] {
        &self.weights
    }

    /// Subgame accessor for tests/exports: (leaf node id, flop index).
    pub fn subgame(&self, node_id: usize, m: usize) -> &FlopSolver {
        &self.leaves[self.leaf_of[node_id]].subgames[m]
    }

    pub fn betting_leaf_node_ids(&self) -> Vec<usize> {
        self.leaves.iter().map(|l| l.node_id).collect()
    }

    /// Total bytes currently allocated across all subgame tables.
    pub fn table_bytes(&self) -> usize {
        self.leaves
            .iter()
            .flat_map(|l| l.subgames.iter())
            .map(|s| s.table_bytes())
            .sum()
    }

    /// Σ_o opp_reach[o] · compat(c,o) · Z(c,o) per combo c — the fold-
    /// terminal and normalizer measure of the M-flop game. O(N²) with an
    /// O(1) Z lookup (design §3).
    fn z_weighted_compat(&self, opp_reach: &[f64; N]) -> Vec<f64> {
        let mut out = vec![0.0f64; N];
        for (c, oc) in out.iter_mut().enumerate() {
            let (c0, c1) = self.combos[c];
            let mc = self.block_mask[c];
            let mut acc = 0.0;
            for o in 0..N {
                let w = opp_reach[o];
                if w == 0.0 {
                    continue;
                }
                let (o0, o1) = self.combos[o];
                if o0 == c0 || o0 == c1 || o1 == c0 || o1 == c1 {
                    continue;
                }
                acc += w * self.zsum[(mc | self.block_mask[o]) as usize];
            }
            *oc = acc;
        }
        out
    }

    /// All-in preflop leaf values under μ: per combo c,
    /// Σ_o w_o Σ_{m legal} w_m (eq_m(c,o)·pot − contrib), in bb.
    #[doc(hidden)]
    pub fn allin_values(
        &self,
        state: &crate::game::BettingState,
        traverser: u8,
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let pot = state.pot() as f64;
        let contrib = state.contrib[traverser as usize] as f64;
        let m_count = self.flops.len();
        let mut out = vec![0.0f64; N];
        for (c, val) in out.iter_mut().enumerate() {
            let (c0, c1) = self.combos[c];
            let mc = self.block_mask[c];
            let mut acc = 0.0;
            for o in 0..N {
                let w = opp_reach[o];
                if w == 0.0 {
                    continue;
                }
                let (o0, o1) = self.combos[o];
                if o0 == c0 || o0 == c1 || o1 == c0 || o1 == c1 {
                    continue;
                }
                let blocked = mc | self.block_mask[o];
                for m in 0..m_count {
                    if blocked & (1 << m) == 0 {
                        let eq = self.allin_eq[m][c * N + o] as f64;
                        acc += w * self.weights[m] * (eq * pot - contrib);
                    }
                }
            }
            *val = acc / 100.0;
        }
        out
    }

    /// Sequential reference run (subgames visited in preflop DFS order).
    /// Kept as the bit-exactness baseline for the parallel path.
    pub fn run_sequential(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;
                self.traverse(0, traverser, &reach, &opp, None);
            }
        }
    }

    /// Parallel run: per traversal, (1) walk the preflop tree top-down
    /// collecting the reach pair at every betting leaf (strategies come
    /// from regrets, which this pass does not touch), (2) traverse all
    /// (leaf, m) subgames in parallel — their tables are disjoint —
    /// aggregating each leaf's M values in fixed order, (3) replay the
    /// preflop DFS with the precomputed leaf values, applying the same
    /// updates as the sequential path. Phases 1–3 are equivalent to the
    /// DFS reordering of independent work, so results are BIT-IDENTICAL
    /// to `run_sequential` (pinned by test).
    pub fn run(&mut self, iterations: u32) {
        use rayon::prelude::*;
        for _ in 0..iterations {
            self.iteration += 1;
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;

                // Phase 1: reach pairs at betting leaves.
                let mut at_leaf: Vec<Option<([f64; N], [f64; N])>> =
                    vec![None; self.leaves.len()];
                self.collect_leaf_reaches(0, traverser, &reach, &opp, &mut at_leaf);

                // Phase 2: all (leaf, m) subgames in parallel.
                let iter = self.iteration;
                let weights = self.weights.clone();
                let block_mask = &self.block_mask;
                let m_count = self.flops.len();
                let leaf_values: Vec<Option<Vec<f64>>> = self
                    .leaves
                    .par_iter_mut()
                    .zip(at_leaf.par_iter())
                    .map(|(leaf, reaches)| {
                        let (r, o) = reaches.as_ref()?;
                        let per_m: Vec<Vec<f64>> = leaf
                            .subgames
                            .par_iter_mut()
                            .enumerate()
                            .map(|(m, sub)| {
                                let mut rm = *r;
                                let mut om = *o;
                                for c in 0..N {
                                    if block_mask[c] & (1 << m) != 0 {
                                        rm[c] = 0.0;
                                        om[c] = 0.0;
                                    }
                                }
                                sub.subgame_traverse(traverser, &rm, &om, iter)
                            })
                            .collect();
                        // Fixed-order aggregation keeps f64 sums identical
                        // to the sequential path.
                        let mut out = vec![0.0f64; N];
                        for (m, v) in per_m.iter().enumerate().take(m_count) {
                            let w = weights[m];
                            for c in 0..N {
                                if block_mask[c] & (1 << m) == 0 {
                                    out[c] += w * v[c];
                                }
                            }
                        }
                        Some(out)
                    })
                    .collect();

                // Phase 3: preflop DFS with injected leaf values.
                self.traverse(0, traverser, &reach, &opp, Some(&leaf_values));
            }
        }
    }

    /// Phase-1 walk: descend every action branch propagating both reach
    /// vectors; record them at betting leaves. Reads regrets only.
    fn collect_leaf_reaches(
        &self,
        node_id: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        out: &mut Vec<Option<([f64; N], [f64; N])>>,
    ) {
        match self.preflop_tree.nodes[node_id].kind {
            NodeKind::NextStreet { pot_type } => {
                if pot_type != PotType::AllInPreflop {
                    out[self.leaf_of[node_id]] = Some((*reach, *opp_reach));
                }
            }
            NodeKind::Action { actor } => {
                let na = self.preflop_tree.nodes[node_id].children.len();
                let strat = self.node_strategy(node_id, na);
                for a in 0..na {
                    let child = self.preflop_tree.nodes[node_id].children[a].1;
                    if actor == traverser {
                        let mut nr = *reach;
                        for c in 0..N {
                            nr[c] *= strat[a * N + c];
                        }
                        self.collect_leaf_reaches(child, traverser, &nr, opp_reach, out);
                    } else {
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] *= strat[a * N + c];
                        }
                        self.collect_leaf_reaches(child, traverser, reach, &no, out);
                    }
                }
            }
            _ => {}
        }
    }

    /// Per-combo masked reach pair entering flop m.
    fn masked(&self, m: usize, v: &[f64; N]) -> [f64; N] {
        let mut out = *v;
        for c in 0..N {
            if self.block_mask[c] & (1 << m) != 0 {
                out[c] = 0.0;
            }
        }
        out
    }

    /// Counterfactual values (bb) for `traverser` at a preflop node.
    /// `leaf_values`: phase-2 results (parallel path); None = compute
    /// subgames inline in DFS order (sequential path).
    fn traverse(
        &mut self,
        node_id: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        leaf_values: Option<&Vec<Option<Vec<f64>>>>,
    ) -> Vec<f64> {
        let kind = self.preflop_tree.nodes[node_id].kind;
        match kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.preflop_tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[traverser as usize] as f64 / 100.0;
                self.z_weighted_compat(opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::NextStreet { pot_type } => {
                let state = self.preflop_tree.nodes[node_id].state;
                if pot_type == PotType::AllInPreflop {
                    return self.allin_values(&state, traverser, opp_reach);
                }
                let leaf = self.leaf_of[node_id];
                if let Some(values) = leaf_values {
                    return values[leaf]
                        .clone()
                        .expect("phase 1 must have reached every visited leaf");
                }
                let iter = self.iteration;
                let m_count = self.flops.len();
                let mut out = vec![0.0f64; N];
                for m in 0..m_count {
                    let r = self.masked(m, reach);
                    let o = self.masked(m, opp_reach);
                    let v =
                        self.leaves[leaf].subgames[m].subgame_traverse(traverser, &r, &o, iter);
                    let w = self.weights[m];
                    for c in 0..N {
                        if self.block_mask[c] & (1 << m) == 0 {
                            out[c] += w * v[c];
                        }
                    }
                }
                out
            }
            NodeKind::Showdown | NodeKind::Chance { .. } => {
                unreachable!("preflop trees have no showdown/chance nodes")
            }
            NodeKind::Action { actor } => {
                let na = self.preflop_tree.nodes[node_id].children.len();
                let strat = self.node_strategy(node_id, na);
                if actor == traverser {
                    let mut action_vals: Vec<Vec<f64>> = Vec::with_capacity(na);
                    for a in 0..na {
                        let child = self.preflop_tree.nodes[node_id].children[a].1;
                        let mut nr = *reach;
                        for c in 0..N {
                            nr[c] *= strat[a * N + c];
                        }
                        action_vals.push(self.traverse(child, traverser, &nr, opp_reach, leaf_values));
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
                        let child = self.preflop_tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] *= strat[a * N + c];
                        }
                        let av = self.traverse(child, traverser, reach, &no, leaf_values);
                        for c in 0..N {
                            ev[c] += av[c];
                        }
                    }
                    ev
                }
            }
        }
    }

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

    /// Normalized average strategy for one combo at a preflop node.
    pub fn average_strategy(&self, node_id: usize, combo: usize) -> Vec<f64> {
        let na = self.preflop_tree.nodes[node_id].children.len();
        let ssum = &self.strat_sum[node_id];
        let total: f64 = (0..na).map(|a| ssum[a * N + combo]).sum();
        if total > 0.0 {
            (0..na).map(|a| ssum[a * N + combo] / total).collect()
        } else {
            vec![1.0 / na as f64; na]
        }
    }

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

    /// Range-weighted aggregate strategy at a preflop node for display.
    pub fn aggregate_strategy(&self, node_id: usize) -> Vec<(String, f64)> {
        let node = &self.preflop_tree.nodes[node_id];
        let actor = match node.kind {
            NodeKind::Action { actor } => actor as usize,
            _ => panic!("not an action node"),
        };
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

    // ----- Exact best response on the M-flop game ------------------------

    fn br_values(&self, node_id: usize, br_player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        match self.preflop_tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.preflop_tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[br_player as usize] as f64 / 100.0;
                self.z_weighted_compat(opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::NextStreet { pot_type } => {
                let state = self.preflop_tree.nodes[node_id].state;
                if pot_type == PotType::AllInPreflop {
                    return self.allin_values(&state, br_player, opp_reach);
                }
                let leaf = self.leaf_of[node_id];
                let mut out = vec![0.0f64; N];
                for m in 0..self.flops.len() {
                    let o = self.masked(m, opp_reach);
                    let v = self.leaves[leaf].subgames[m].subgame_br_values(br_player, &o);
                    let w = self.weights[m];
                    for c in 0..N {
                        if self.block_mask[c] & (1 << m) == 0 {
                            out[c] += w * v[c];
                        }
                    }
                }
                out
            }
            NodeKind::Showdown | NodeKind::Chance { .. } => unreachable!(),
            NodeKind::Action { actor } => {
                let na = self.preflop_tree.nodes[node_id].children.len();
                if actor == br_player {
                    let mut best = vec![f64::NEG_INFINITY; N];
                    for a in 0..na {
                        let child = self.preflop_tree.nodes[node_id].children[a].1;
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
                        let child = self.preflop_tree.nodes[node_id].children[a].1;
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

    fn avg_values(&self, node_id: usize, player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        match self.preflop_tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.preflop_tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[player as usize] as f64 / 100.0;
                self.z_weighted_compat(opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::NextStreet { pot_type } => {
                let state = self.preflop_tree.nodes[node_id].state;
                if pot_type == PotType::AllInPreflop {
                    return self.allin_values(&state, player, opp_reach);
                }
                let leaf = self.leaf_of[node_id];
                let mut out = vec![0.0f64; N];
                for m in 0..self.flops.len() {
                    let o = self.masked(m, opp_reach);
                    let v = self.leaves[leaf].subgames[m].subgame_avg_values(player, &o);
                    let w = self.weights[m];
                    for c in 0..N {
                        if self.block_mask[c] & (1 << m) == 0 {
                            out[c] += w * v[c];
                        }
                    }
                }
                out
            }
            NodeKind::Showdown | NodeKind::Chance { .. } => unreachable!(),
            NodeKind::Action { actor } => {
                let na = self.preflop_tree.nodes[node_id].children.len();
                let strat = self.avg_matrix(node_id, na);
                let mut ev = vec![0.0; N];
                if actor == player {
                    for a in 0..na {
                        let child = self.preflop_tree.nodes[node_id].children[a].1;
                        let v = self.avg_values(child, player, opp_reach);
                        for c in 0..N {
                            ev[c] += strat[a * N + c] * v[c];
                        }
                    }
                } else {
                    for a in 0..na {
                        let child = self.preflop_tree.nodes[node_id].children[a].1;
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
    /// exact on the M-flop game (normalizer Σ w0·w1·compat·Z).
    pub fn game_value_p0(&self) -> f64 {
        let r0 = self.ranges[0].weights;
        let r1 = self.ranges[1].weights;
        let vals = self.avg_values(0, 0, &r1);
        let zc = self.z_weighted_compat(&r1);
        let mut num = 0.0;
        let mut z = 0.0;
        for c in 0..N {
            if r0[c] > 0.0 {
                num += r0[c] * vals[c];
                z += r0[c] * zc[c];
            }
        }
        if z > 0.0 {
            num / z
        } else {
            0.0
        }
    }

    /// Exact exploitability (bb/hand) of the exported CFR profile on
    /// the M-flop abstract game: (BR_sb + BR_bb) / 2.
    pub fn exploitability_bb(&self) -> ExplReport {
        let mut br_value = [0.0f64; 2];
        #[allow(clippy::needless_range_loop)]
        for p in 0..2usize {
            let own = self.ranges[p].weights;
            let opp = self.ranges[1 - p].weights;
            let vals = self.br_values(0, p as u8, &opp);
            let zc = self.z_weighted_compat(&opp);
            let mut num = 0.0;
            let mut z = 0.0;
            for c in 0..N {
                if own[c] > 0.0 {
                    num += own[c] * vals[c];
                    z += own[c] * zc[c];
                }
            }
            br_value[p] = if z > 0.0 { num / z } else { 0.0 };
        }
        ExplReport::zero_sum(br_value)
    }
}
