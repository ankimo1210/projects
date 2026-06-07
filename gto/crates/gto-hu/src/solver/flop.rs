//! Exact-combo vector CFR for a fixed flop board. Turn and river are
//! nested public chance nodes: enumerated exactly (tests, exploitability)
//! or sampled (public chance sampling for larger runs). Design spec §6–§8.
//!
//! Chance math (mirrors the turn+river solver): per (hero, villain) deal
//! exactly 45 of the 49 public turn cards are legal (52 − 3 board − 2 − 2),
//! and 44 of the 48 public river cards (52 − 4 − 2 − 2). Enumeration
//! weights each surviving card 1/45 (turn) and 1/44 (river); sampling
//! draws uniform from the public cards and scales by 49/45, which is
//! unbiased exactly as in the turn+river case.
//!
//! `ChanceMode::Sample` samples the TURN card only; the river stage is
//! always enumerated. Sampling both stages is also unbiased but spreads
//! river updates over 49 × 48 = 2352 contexts — at practical iteration
//! counts each river infoset would receive only a handful of updates and
//! exploitability stalls (measured: 5.9 bb after 10k double-sampled
//! iterations on a small tree). Sampling the turn and enumerating the
//! river gives every visited river infoset a full-support update, the
//! same training density per turn branch as the turn+river solver.
//!
//! Storage: dense per-context tables explode on flop trees
//! (49 × 48 = 2352 river contexts per node), so slabs are allocated
//! lazily per (node, context) on first regret/strategy write. Unvisited
//! contexts read as uniform strategies. `dense_table_bytes` reports the
//! fully-allocated size so callers can refuse infeasible configs up
//! front (fail loud, spec §8).

use std::collections::HashMap;

use super::regret::regret_matching;
use super::rng::SplitMix64;
use super::showdown::{weighted_compat, ShowdownTable};
use super::turn_river::ChanceMode;
use super::variant::CfrVariant;
use super::vector::ExplReport;
use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::game::Street;
use crate::ranges::{all_combos, Range, NUM_COMBOS};
use crate::tree::{NodeKind, Tree};

const N: usize = NUM_COMBOS;
/// Public turn cards off a 3-card flop.
const N_TURNS: usize = 49;
/// Public river cards off a 4-card board.
const N_RIVERS: usize = 48;
/// Legal turns per (hero, villain) deal: 52 − 3 − 2 − 2.
const LEGAL_TURNS: f64 = 45.0;
/// Legal rivers per (hero, villain) deal: 52 − 4 − 2 − 2.
const LEGAL_RIVERS: f64 = 44.0;

/// Lazily allocated per-context tables for one node: slab `ctx` holds
/// `slab_len` f64 values, created zeroed on first mutable access.
struct NodeTable {
    slabs: Vec<Option<Box<[f64]>>>,
    slab_len: usize,
}

impl NodeTable {
    fn new(n_ctx: usize, slab_len: usize) -> Self {
        NodeTable {
            slabs: vec![None; n_ctx],
            slab_len,
        }
    }

    fn empty() -> Self {
        NodeTable {
            slabs: Vec::new(),
            slab_len: 0,
        }
    }

    fn get_mut(&mut self, ctx: usize) -> &mut [f64] {
        self.slabs[ctx].get_or_insert_with(|| vec![0.0; self.slab_len].into_boxed_slice())
    }

    fn get(&self, ctx: usize) -> Option<&[f64]> {
        self.slabs.get(ctx).and_then(|s| s.as_deref())
    }

    fn bytes(&self) -> usize {
        self.slabs.iter().flatten().map(|s| s.len() * 8).sum()
    }
}

/// Context for one traversal: indices into `turns` / `rivers[t]`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Ctx {
    turn: Option<usize>,
    river: Option<usize>,
}

impl Ctx {
    const PRE: Ctx = Ctx {
        turn: None,
        river: None,
    };
}

pub struct FlopSolver {
    pub tree: Tree,
    pub flop_board: [u8; 3],
    pub ranges: [Range; 2],
    pub variant: CfrVariant,
    pub mode: ChanceMode,
    /// Public turn cards (off the flop), ascending. Index = turn ctx.
    turns: Vec<u8>,
    /// rivers[t] = public river cards off flop + turns[t], ascending.
    /// Index within = river ctx.
    rivers: Vec<Vec<u8>>,
    /// Showdown tables shared between (t, r) and the mirrored (r, t)
    /// context — the 5-card board is the same set.
    tables: Vec<ShowdownTable>,
    /// [t][r] → index into `tables`.
    table_of: Vec<Vec<usize>>,
    regrets: Vec<NodeTable>,
    strat_sum: Vec<NodeTable>,
    rng: SplitMix64,
    iteration: u32,
    combos: Vec<(u8, u8)>,
}

#[inline]
fn combo_blocks(combo: (u8, u8), card: u8) -> bool {
    combo.0 == card || combo.1 == card
}

fn zero_card(combos: &[(u8, u8)], card: u8, weights: &mut [f64; N]) {
    for (i, &(a, b)) in combos.iter().enumerate() {
        if a == card || b == card {
            weights[i] = 0.0;
        }
    }
}

/// Per-street context multiplicity inside a flop tree.
fn ctx_count(street: Street) -> usize {
    match street {
        Street::Flop => 1,
        Street::Turn => N_TURNS,
        Street::River => N_TURNS * N_RIVERS,
        Street::Preflop => unreachable!("no preflop nodes in a flop tree"),
    }
}

/// Fully-dense table size (regrets + strategy sums) for a flop tree.
/// Use this to refuse infeasible configs before allocating anything.
pub fn dense_table_bytes(tree: &Tree) -> usize {
    tree.nodes
        .iter()
        .map(|n| match n.kind {
            NodeKind::Action { .. } => {
                2 * 8 * ctx_count(n.state.street) * n.children.len() * N
            }
            _ => 0,
        })
        .sum()
}

impl FlopSolver {
    pub fn new(
        tree: Tree,
        flop_board: [u8; 3],
        mut ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
    ) -> Self {
        assert_eq!(
            tree.nodes[0].state.street,
            Street::Flop,
            "root must be a flop node (build with build_flop_tree)"
        );
        let mut seen = [false; 52];
        for &c in &flop_board {
            assert!(!seen[c as usize], "duplicate card on flop board");
            seen[c as usize] = true;
        }
        for r in &mut ranges {
            r.remove_blockers(&flop_board);
        }
        let turns: Vec<u8> = (0..52u8).filter(|c| !flop_board.contains(c)).collect();
        debug_assert_eq!(turns.len(), N_TURNS);
        let rivers: Vec<Vec<u8>> = turns
            .iter()
            .map(|&t| {
                (0..52u8)
                    .filter(|&c| !flop_board.contains(&c) && c != t)
                    .collect()
            })
            .collect();

        // Build one ShowdownTable per unordered {turn, river} pair.
        let mut tables: Vec<ShowdownTable> = Vec::with_capacity(N_TURNS * N_RIVERS / 2);
        let mut pair_idx: HashMap<(u8, u8), usize> = HashMap::new();
        let mut table_of: Vec<Vec<usize>> = Vec::with_capacity(N_TURNS);
        for (ti, &t) in turns.iter().enumerate() {
            let mut row = Vec::with_capacity(N_RIVERS);
            for &r in &rivers[ti] {
                let key = (t.min(r), t.max(r));
                let idx = *pair_idx.entry(key).or_insert_with(|| {
                    let mut b5 = [0u8; 5];
                    b5[..3].copy_from_slice(&flop_board);
                    b5[3] = key.0;
                    b5[4] = key.1;
                    tables.push(ShowdownTable::new(&b5));
                    tables.len() - 1
                });
                row.push(idx);
            }
            table_of.push(row);
        }

        let alloc = |tree: &Tree| -> Vec<NodeTable> {
            tree.nodes
                .iter()
                .map(|n| match n.kind {
                    NodeKind::Action { .. } => NodeTable::new(
                        ctx_count(n.state.street),
                        n.children.len() * N,
                    ),
                    _ => NodeTable::empty(),
                })
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        let seed = match mode {
            ChanceMode::Sample { seed } => seed,
            ChanceMode::Enumerate => 0,
        };
        FlopSolver {
            tree,
            flop_board,
            ranges,
            variant,
            mode,
            turns,
            rivers,
            tables,
            table_of,
            regrets,
            strat_sum,
            rng: SplitMix64::new(seed),
            iteration: 0,
            combos: all_combos(),
        }
    }

    pub fn turns(&self) -> &[u8] {
        &self.turns
    }

    pub fn rivers(&self, turn_ctx: usize) -> &[u8] {
        &self.rivers[turn_ctx]
    }

    /// Bytes currently allocated for regret + average-strategy tables
    /// (grows with visited contexts; bounded by `dense_table_bytes`).
    pub fn table_bytes(&self) -> usize {
        self.regrets
            .iter()
            .chain(self.strat_sum.iter())
            .map(|t| t.bytes())
            .sum()
    }

    /// Slab context index for a node given the traversal context.
    fn ctx_index(&self, node_id: usize, ctx: Ctx) -> usize {
        match self.tree.nodes[node_id].state.street {
            Street::Flop => 0,
            Street::Turn => ctx.turn.expect("turn node requires a turn card"),
            Street::River => {
                ctx.turn.expect("river node requires a turn card") * N_RIVERS
                    + ctx.river.expect("river node requires a river card")
            }
            Street::Preflop => unreachable!(),
        }
    }

    fn showdown_table(&self, ctx: Ctx) -> &ShowdownTable {
        let t = ctx.turn.expect("showdown requires a turn card");
        let r = ctx.river.expect("showdown requires a river card");
        &self.tables[self.table_of[t][r]]
    }

    pub fn run(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;
                self.traverse(0, traverser, &reach, &opp, Ctx::PRE);
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
        ctx: Ctx,
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
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(traverser))[traverser as usize] as f64 / 100.0;
                let table = self.showdown_table(ctx);
                table
                    .diff(&self.combos, opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { child } => {
                // The chance node's own street says what it deals. Only
                // the turn deal is ever sampled (see module docs); the
                // river deal is always enumerated.
                let deal_street = self.tree.nodes[node_id].state.street;
                match self.mode {
                    ChanceMode::Sample { .. } if deal_street == Street::Flop => {
                        self.chance_sample(child, deal_street, traverser, reach, opp_reach, ctx)
                    }
                    _ => {
                        self.chance_enumerate(child, deal_street, traverser, reach, opp_reach, ctx)
                    }
                }
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let cx = self.ctx_index(node_id, ctx);
                let strat = self.node_strategy(node_id, cx, na);

                if actor == traverser {
                    let mut action_vals: Vec<Vec<f64>> = Vec::with_capacity(na);
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut nr = *reach;
                        for c in 0..N {
                            nr[c] *= strat[a * N + c];
                        }
                        action_vals.push(self.traverse(child, traverser, &nr, opp_reach, ctx));
                    }
                    let mut ev = vec![0.0; N];
                    for c in 0..N {
                        for (a, av) in action_vals.iter().enumerate() {
                            ev[c] += strat[a * N + c] * av[c];
                        }
                    }
                    // Same per-iteration discount/update discipline as the
                    // turn+river solver: in sampled mode unvisited
                    // (node, ctx) slabs keep their stored sums (lazy-
                    // discount chance-sampled MCCFR).
                    let t = self.iteration;
                    let (sd, sw) = (
                        self.variant.strategy_discount(t),
                        self.variant.strategy_weight(t),
                    );
                    let variant = self.variant;
                    let reg = self.regrets[node_id].get_mut(cx);
                    #[allow(clippy::needless_range_loop)]
                    for c in 0..N {
                        for a in 0..na {
                            let i = a * N + c;
                            let discounted = reg[i] * variant.regret_discount(reg[i], t);
                            reg[i] =
                                variant.accumulate_regret(discounted, action_vals[a][c] - ev[c]);
                        }
                    }
                    let ssum = self.strat_sum[node_id].get_mut(cx);
                    #[allow(clippy::needless_range_loop)]
                    for c in 0..N {
                        for a in 0..na {
                            let i = a * N + c;
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
                        let av = self.traverse(child, traverser, reach, &no, ctx);
                        for c in 0..N {
                            ev[c] += av[c];
                        }
                    }
                    ev
                }
            }
        }
    }

    /// (cards, legal-per-deal, next-ctx builder) for one chance stage.
    fn stage_cards(&self, deal_street: Street, ctx: Ctx) -> (Vec<(usize, u8)>, f64) {
        match deal_street {
            Street::Flop => (
                self.turns.iter().copied().enumerate().collect(),
                LEGAL_TURNS,
            ),
            Street::Turn => {
                let t = ctx.turn.expect("river deal requires a turn ctx");
                (
                    self.rivers[t].iter().copied().enumerate().collect(),
                    LEGAL_RIVERS,
                )
            }
            s => unreachable!("chance deal on {s:?}"),
        }
    }

    fn child_ctx(deal_street: Street, ctx: Ctx, card_idx: usize) -> Ctx {
        match deal_street {
            Street::Flop => Ctx {
                turn: Some(card_idx),
                river: None,
            },
            Street::Turn => Ctx {
                turn: ctx.turn,
                river: Some(card_idx),
            },
            s => unreachable!("chance deal on {s:?}"),
        }
    }

    fn chance_enumerate(
        &mut self,
        child: usize,
        deal_street: Street,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        ctx: Ctx,
    ) -> Vec<f64> {
        let (cards, legal) = self.stage_cards(deal_street, ctx);
        let w = 1.0 / legal;
        let mut ev = vec![0.0; N];
        for (idx, card) in cards {
            let mut r = *reach;
            let mut o = *opp_reach;
            zero_card(&self.combos, card, &mut r);
            zero_card(&self.combos, card, &mut o);
            let next = Self::child_ctx(deal_street, ctx, idx);
            let v = self.traverse(child, traverser, &r, &o, next);
            for c in 0..N {
                if !combo_blocks(self.combos[c], card) {
                    ev[c] += w * v[c];
                }
            }
        }
        ev
    }

    fn chance_sample(
        &mut self,
        child: usize,
        deal_street: Street,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        ctx: Ctx,
    ) -> Vec<f64> {
        let (cards, legal) = self.stage_cards(deal_street, ctx);
        let n_pub = cards.len();
        let pick = self.rng.next_index(n_pub);
        let (idx, card) = cards[pick];
        let scale = n_pub as f64 / legal; // 49/45 (turn) or 48/44 (river)
        let mut r = *reach;
        let mut o = *opp_reach;
        zero_card(&self.combos, card, &mut r);
        zero_card(&self.combos, card, &mut o);
        let next = Self::child_ctx(deal_street, ctx, idx);
        let v = self.traverse(child, traverser, &r, &o, next);
        let mut ev = vec![0.0; N];
        for c in 0..N {
            if !combo_blocks(self.combos[c], card) {
                ev[c] = scale * v[c];
            }
        }
        ev
    }

    /// Current per-combo strategy at a (node, ctx): [action * N + combo].
    /// Unallocated slabs are uniform (zero regrets).
    fn node_strategy(&self, node_id: usize, cx: usize, na: usize) -> Vec<f64> {
        let mut strat = vec![0.0; na * N];
        match self.regrets[node_id].get(cx) {
            Some(reg) => {
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
            }
            None => {
                let u = 1.0 / na as f64;
                strat.iter_mut().for_each(|v| *v = u);
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

    /// Range weight for exports: zero when the combo holds the context's
    /// turn or river card (such infosets are unreachable).
    pub fn export_weight(
        &self,
        actor: usize,
        turn_ctx: Option<usize>,
        river_ctx: Option<usize>,
        combo: usize,
    ) -> f64 {
        if let Some(t) = turn_ctx {
            if combo_blocks(self.combos[combo], self.turns[t]) {
                return 0.0;
            }
            if let Some(r) = river_ctx {
                if combo_blocks(self.combos[combo], self.rivers[t][r]) {
                    return 0.0;
                }
            }
        }
        self.ranges[actor].weights[combo]
    }

    /// Normalized average strategy for one combo at one (node, ctx).
    pub fn average_strategy(
        &self,
        node_id: usize,
        turn_ctx: Option<usize>,
        river_ctx: Option<usize>,
        combo: usize,
    ) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        let cx = self.ctx_index(
            node_id,
            Ctx {
                turn: turn_ctx,
                river: river_ctx,
            },
        );
        match self.strat_sum[node_id].get(cx) {
            Some(ssum) => {
                let total: f64 = (0..na).map(|a| ssum[a * N + combo]).sum();
                if total > 0.0 {
                    (0..na).map(|a| ssum[a * N + combo] / total).collect()
                } else {
                    vec![1.0 / na as f64; na]
                }
            }
            None => vec![1.0 / na as f64; na],
        }
    }

    /// Range-weighted aggregate strategy at a (node, ctx) for display.
    pub fn aggregate_strategy(
        &self,
        node_id: usize,
        turn_ctx: Option<usize>,
        river_ctx: Option<usize>,
    ) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[node_id];
        let actor = self.actor_at(node_id) as usize;
        let na = node.children.len();
        let mut freq = vec![0.0; na];
        let mut total = 0.0;
        for c in 0..N {
            let w = self.export_weight(actor, turn_ctx, river_ctx, c);
            if w == 0.0 {
                continue;
            }
            let s = self.average_strategy(node_id, turn_ctx, river_ctx, c);
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
    // Chance nodes are ALWAYS enumerated here, regardless of training
    // mode: exploitability and game value are exact.

    /// Normalized average strategy for ALL combos at a (node, ctx):
    /// [action * N + combo]. One slab pass — the per-combo
    /// `average_strategy` would allocate a Vec per combo and dominates
    /// best-response time on flop trees (49×48 contexts).
    fn avg_matrix(&self, node_id: usize, ctx: Ctx, na: usize) -> Vec<f64> {
        let cx = self.ctx_index(node_id, ctx);
        let mut strat = vec![1.0 / na as f64; na * N];
        if let Some(ssum) = self.strat_sum[node_id].get(cx) {
            for c in 0..N {
                let total: f64 = (0..na).map(|a| ssum[a * N + c]).sum();
                if total > 0.0 {
                    for a in 0..na {
                        strat[a * N + c] = ssum[a * N + c] / total;
                    }
                }
            }
        }
        strat
    }

    /// Counterfactual BR values for `br_player` (opponent plays the
    /// average strategy).
    fn br_values(
        &self,
        node_id: usize,
        br_player: u8,
        opp_reach: &[f64; N],
        ctx: Ctx,
    ) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
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
                let table = self.showdown_table(ctx);
                table
                    .diff(&self.combos, opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { child } => {
                let deal_street = self.tree.nodes[node_id].state.street;
                let (cards, legal) = self.stage_cards(deal_street, ctx);
                let w = 1.0 / legal;
                let mut ev = vec![0.0; N];
                for (idx, card) in cards {
                    let mut o = *opp_reach;
                    zero_card(&self.combos, card, &mut o);
                    let next = Self::child_ctx(deal_street, ctx, idx);
                    let v = self.br_values(child, br_player, &o, next);
                    for c in 0..N {
                        if !combo_blocks(self.combos[c], card) {
                            ev[c] += w * v[c];
                        }
                    }
                }
                ev
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                if actor == br_player {
                    let mut best = vec![f64::NEG_INFINITY; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.br_values(child, br_player, opp_reach, ctx);
                        for c in 0..N {
                            if v[c] > best[c] {
                                best[c] = v[c];
                            }
                        }
                    }
                    best
                } else {
                    let strat = self.avg_matrix(node_id, ctx, na);
                    let mut ev = vec![0.0; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] = opp_reach[c] * strat[a * N + c];
                        }
                        let v = self.br_values(child, br_player, &no, ctx);
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
    /// average strategy (chance enumerated exactly).
    fn avg_values(
        &self,
        node_id: usize,
        player: u8,
        opp_reach: &[f64; N],
        ctx: Ctx,
    ) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
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
                let table = self.showdown_table(ctx);
                table
                    .diff(&self.combos, opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { child } => {
                let deal_street = self.tree.nodes[node_id].state.street;
                let (cards, legal) = self.stage_cards(deal_street, ctx);
                let w = 1.0 / legal;
                let mut ev = vec![0.0; N];
                for (idx, card) in cards {
                    let mut o = *opp_reach;
                    zero_card(&self.combos, card, &mut o);
                    let next = Self::child_ctx(deal_street, ctx, idx);
                    let v = self.avg_values(child, player, &o, next);
                    for c in 0..N {
                        if !combo_blocks(self.combos[c], card) {
                            ev[c] += w * v[c];
                        }
                    }
                }
                ev
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let strat = self.avg_matrix(node_id, ctx, na);
                let mut ev = vec![0.0; N];
                if actor == player {
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.avg_values(child, player, opp_reach, ctx);
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
                        let v = self.avg_values(child, player, &no, ctx);
                        for c in 0..N {
                            ev[c] += v[c];
                        }
                    }
                }
                ev
            }
        }
    }

    /// Game value (bb/hand) to player 0 (SB/IP) under avg-vs-avg play.
    /// Always exact (chance enumerated), even when training used sampling.
    pub fn game_value_p0(&self) -> f64 {
        let r0 = self.ranges[0].weights;
        let r1 = self.ranges[1].weights;
        let vals = self.avg_values(0, 0, &r1, Ctx::PRE);
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

    /// Exploitability in bb/hand: (BR_sb + BR_bb) / 2. Always exact
    /// (chance enumerated), even when training used sampling.
    pub fn exploitability_bb(&self) -> ExplReport {
        let mut br_value = [0.0f64; 2];
        #[allow(clippy::needless_range_loop)]
        for p in 0..2usize {
            let own = self.ranges[p].weights;
            let opp = self.ranges[1 - p].weights;
            let vals = self.br_values(0, p as u8, &opp, Ctx::PRE);
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
