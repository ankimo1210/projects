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
use crate::ranges::{Range, NUM_COMBOS};
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
    /// Strategy-table width at river nodes: 1326 (exact) or K_r
    /// (strength-percentile buckets — bucketing design spec §3).
    river_dim: usize,
    /// combo → bucket per shared (turn, river) pair, parallel to
    /// `tables`. None when river is exact.
    bucket_maps: Option<Vec<Vec<u16>>>,
    /// Strategy-table width at turn nodes: 1326 (exact) or K_t
    /// (mean-river-percentile buckets).
    turn_dim: usize,
    /// combo → bucket per turn card. None when the turn is exact.
    turn_bucket_maps: Option<Vec<Vec<u16>>>,
    regrets: Vec<NodeTable>,
    strat_sum: Vec<NodeTable>,
    /// Last iteration in which a (node, slab-ctx) was discounted. `[node]`
    /// is empty for non-action nodes, else `ctx_count(street)` scalars.
    /// Under sampled chance (turn sampled, river enumerated) a slab is
    /// visited only when its turn card is drawn (~1/49 of iterations), so
    /// on each visit it catches up the discounts of the skipped iterations
    /// (B7 — mirrors the turn+river solver). Unused under enumeration.
    last_discount_iter: Vec<Vec<u32>>,
    /// DCFR regret-discount prefix products (pos/neg). See the same fields
    /// on `TurnRiverSolver`. Empty for non-DCFR (catch-up is always 1.0).
    regret_disc_prefix_pos: Vec<f64>,
    regret_disc_prefix_neg: Vec<f64>,
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

/// Strategy-space abstraction per street (0 = exact combos).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Abstraction {
    /// River strength-percentile buckets.
    pub buckets_river: usize,
    /// Turn mean-river-percentile buckets.
    pub buckets_turn: usize,
}

/// Fully-dense table size (regrets + strategy sums) for a flop tree
/// with exact-combo storage on every street.
pub fn dense_table_bytes(tree: &Tree) -> usize {
    dense_table_bytes_abstracted(tree, Abstraction::default())
}

/// Dense table size with river strategy rows bucketed to `buckets_river`
/// (0 = exact).
pub fn dense_table_bytes_bucketed(tree: &Tree, buckets_river: usize) -> usize {
    dense_table_bytes_abstracted(
        tree,
        Abstraction {
            buckets_river,
            buckets_turn: 0,
        },
    )
}

/// Dense table size under a street abstraction. The `--max-table-gb`
/// gate uses this.
pub fn dense_table_bytes_abstracted(tree: &Tree, abs: Abstraction) -> usize {
    let river_dim = if abs.buckets_river == 0 { N } else { abs.buckets_river };
    let turn_dim = if abs.buckets_turn == 0 { N } else { abs.buckets_turn };
    tree.nodes
        .iter()
        .map(|n| match n.kind {
            NodeKind::Action { .. } => {
                let dim = match n.state.street {
                    Street::River => river_dim,
                    Street::Turn => turn_dim,
                    _ => N,
                };
                2 * 8 * ctx_count(n.state.street) * n.children.len() * dim
            }
            _ => 0,
        })
        .sum()
}

/// Tier-grouped percentile binning of `scores` over the combos where
/// `live` holds: rank ascending, equal scores share a bucket, bucket =
/// tier_start_rank × k / n_ranked (same discipline as the river
/// `strength_buckets`). Non-live combos get bucket 0.
fn percentile_buckets(scores: &[f32], live: &[bool], k: usize) -> Vec<u16> {
    assert!(k > 0 && k <= u16::MAX as usize + 1);
    let mut ranked: Vec<usize> = (0..scores.len()).filter(|&i| live[i]).collect();
    ranked.sort_by(|&a, &b| scores[a].partial_cmp(&scores[b]).unwrap());
    let n_ranked = ranked.len().max(1);
    let mut out = vec![0u16; scores.len()];
    let mut g = 0;
    while g < ranked.len() {
        let s = scores[ranked[g]];
        let mut h = g;
        while h < ranked.len() && scores[ranked[h]] == s {
            h += 1;
        }
        let b = (g * k / n_ranked) as u16;
        for &i in &ranked[g..h] {
            out[i] = b;
        }
        g = h;
    }
    out
}

impl FlopSolver {
    /// Exact-combo solver (no abstraction).
    pub fn new(
        tree: Tree,
        flop_board: [u8; 3],
        ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
    ) -> Self {
        Self::new_with_buckets(tree, flop_board, ranges, variant, mode, 0)
    }

    /// Solver with river strategy rows bucketed to `buckets_river`
    /// strength-percentile buckets (0 = exact).
    pub fn new_with_buckets(
        tree: Tree,
        flop_board: [u8; 3],
        ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
        buckets_river: usize,
    ) -> Self {
        Self::new_abstracted(
            tree,
            flop_board,
            ranges,
            variant,
            mode,
            Abstraction {
                buckets_river,
                buckets_turn: 0,
            },
        )
    }

    /// Solver under a street abstraction. Traversal, blockers and
    /// payoffs stay per-combo; only regret/strategy STORAGE is shared
    /// (bucketing design spec §2–§5), and the exact best response keeps
    /// exploitability honest about the abstraction loss.
    pub fn new_abstracted(
        tree: Tree,
        flop_board: [u8; 3],
        mut ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
        abs: Abstraction,
    ) -> Self {
        let buckets_river = abs.buckets_river;
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

        let river_dim = if buckets_river == 0 { N } else { buckets_river };
        assert!(river_dim <= N, "more buckets than combos is meaningless");
        // combo → bucket per shared (turn, river) pair (≈3 MB at u16).
        // Any K > 0 builds real maps — K = N is tier-injective bucketing
        // (equal-strength combos share rows), NOT a silent exact
        // fallback (review finding: that no-op made the differential
        // test vacuous).
        let bucket_maps = (buckets_river > 0)
            .then(|| tables.iter().map(|t| t.strength_buckets(river_dim)).collect());

        let turn_dim = if abs.buckets_turn == 0 { N } else { abs.buckets_turn };
        assert!(turn_dim <= N, "more buckets than combos is meaningless");
        // Turn buckets: score = mean strength percentile over the legal
        // rivers of each turn card (bucketing design spec §3, "later"
        // part — now implemented). Same tier-grouped percentile binning
        // as the river.
        let turn_bucket_maps = (abs.buckets_turn > 0).then(|| {
            let pcts: Vec<Vec<f32>> = tables.iter().map(|t| t.strength_percentiles()).collect();
            (0..N_TURNS)
                .map(|ti| {
                    let mut score = vec![0.0f32; N];
                    let mut cnt = vec![0u32; N];
                    for ri in 0..N_RIVERS {
                        let p = &pcts[table_of[ti][ri]];
                        for c in 0..N {
                            if p[c] > 0.0 {
                                score[c] += p[c];
                                cnt[c] += 1;
                            }
                        }
                    }
                    let live: Vec<bool> = cnt.iter().map(|&n| n > 0).collect();
                    for c in 0..N {
                        if cnt[c] > 0 {
                            score[c] /= cnt[c] as f32;
                        }
                    }
                    percentile_buckets(&score, &live, turn_dim)
                })
                .collect()
        });

        let alloc = |tree: &Tree| -> Vec<NodeTable> {
            tree.nodes
                .iter()
                .map(|n| match n.kind {
                    NodeKind::Action { .. } => {
                        let dim = match n.state.street {
                            Street::River => river_dim,
                            Street::Turn => turn_dim,
                            _ => N,
                        };
                        NodeTable::new(ctx_count(n.state.street), n.children.len() * dim)
                    }
                    _ => NodeTable::empty(),
                })
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        let last_discount_iter: Vec<Vec<u32>> = tree
            .nodes
            .iter()
            .map(|n| match n.kind {
                NodeKind::Action { .. } => vec![0u32; ctx_count(n.state.street)],
                _ => Vec::new(),
            })
            .collect();
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
            river_dim,
            bucket_maps,
            turn_dim,
            turn_bucket_maps,
            regrets,
            strat_sum,
            last_discount_iter,
            regret_disc_prefix_pos: vec![1.0],
            regret_disc_prefix_neg: vec![1.0],
            rng: SplitMix64::new(seed),
            iteration: 0,
            combos: crate::ranges::nlhe().combos().to_vec(),
        }
    }

    /// Strategy-row width and combo→row map at a node/context. Streets
    /// without abstraction use the identity over 1326 combos.
    fn row_map(&self, node_id: usize, ctx: Ctx) -> (usize, Option<&[u16]>) {
        match self.tree.nodes[node_id].state.street {
            Street::River => {
                if let Some(maps) = &self.bucket_maps {
                    let t = ctx.turn.expect("river node requires a turn card");
                    let r = ctx.river.expect("river node requires a river card");
                    return (self.river_dim, Some(&maps[self.table_of[t][r]]));
                }
            }
            Street::Turn => {
                if let Some(maps) = &self.turn_bucket_maps {
                    let t = ctx.turn.expect("turn node requires a turn card");
                    return (self.turn_dim, Some(&maps[t]));
                }
            }
            _ => {}
        }
        (N, None)
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
            self.extend_regret_prefix(self.iteration);
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;
                self.traverse(0, traverser, &reach, &opp, Ctx::PRE);
            }
        }
    }

    /// Grow the DCFR regret-discount prefix products to cover iteration `t`
    /// (no-op for non-DCFR variants — the catch-up factor is always 1.0).
    fn extend_regret_prefix(&mut self, t: u32) {
        if !matches!(self.variant, CfrVariant::Dcfr { .. }) {
            return;
        }
        let want = t as usize + 1;
        while self.regret_disc_prefix_pos.len() < want {
            let u = self.regret_disc_prefix_pos.len() as u32; // next iteration index
            let (d_pos, d_neg) = self.variant.regret_discounts(u);
            let last_pos = *self.regret_disc_prefix_pos.last().unwrap();
            let last_neg = *self.regret_disc_prefix_neg.last().unwrap();
            self.regret_disc_prefix_pos.push(last_pos * d_pos);
            self.regret_disc_prefix_neg.push(last_neg * d_neg);
        }
    }

    /// Cumulative regret discount over the skipped gap L+1..t-1 for a stored
    /// regret of the given sign (constant across the gap). `prefix[t-1] /
    /// prefix[L]`; 1.0 when there is no gap (L >= t-1) or for non-DCFR.
    #[inline]
    fn regret_catchup(&self, last: u32, t: u32, nonneg: bool) -> f64 {
        if t <= last + 1 || self.regret_disc_prefix_pos.len() <= 1 {
            return 1.0;
        }
        let prefix = if nonneg {
            &self.regret_disc_prefix_pos
        } else {
            &self.regret_disc_prefix_neg
        };
        prefix[(t - 1) as usize] / prefix[last as usize]
    }

    // ----- Blueprint composition hooks (blueprint design §3) -----------
    // The blueprint's preflop layer owns the iteration counter and the
    // reach vectors entering this subgame. The regret-aggregation weight
    // stays this solver's STATIC export_weight (base range × board
    // mask): the traverser's own preflop strategy is π_i and never
    // enters the counterfactual weighting.

    /// One CFR traversal from the subgame root with external reaches.
    pub fn subgame_traverse(
        &mut self,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        iteration: u32,
    ) -> Vec<f64> {
        self.iteration = iteration;
        self.extend_regret_prefix(iteration);
        self.traverse(0, traverser, reach, opp_reach, Ctx::PRE)
    }

    /// Exact per-combo best-response values at the subgame root.
    pub fn subgame_br_values(&self, br_player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        self.br_values(0, br_player, opp_reach, Ctx::PRE)
    }

    /// Per-combo avg-vs-avg values at the subgame root.
    pub fn subgame_avg_values(&self, player: u8, opp_reach: &[f64; N]) -> Vec<f64> {
        self.avg_values(0, player, opp_reach, Ctx::PRE)
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
            NodeKind::NextStreet { .. } => unreachable!("flop trees have no NextStreet nodes"),
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let cx = self.ctx_index(node_id, ctx);
                let strat = self.node_strategy(node_id, ctx, na);

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
                    //
                    // Bucketed rows (river): per-combo deltas are summed
                    // into the shared row, WEIGHTED by the traverser's
                    // own deal probability w_c (range weight × board
                    // mask) — the chance part of the counterfactual
                    // reach. Without w_c, board-blocked combos (showdown
                    // value 0, fold value < 0) and out-of-range combos
                    // pollute shared rows with phantom "calling is free"
                    // regret (adversarial review: 70× exploitability
                    // inflation on a near-lossless map). Discount +
                    // CFR+/DCFR clipping then apply once per row entry.
                    // Exact mode: w_c = 1 for in-range combos (uniform
                    // ranges) so single-combo rows are untouched; w_c=0
                    // rows simply stay unvisited (unreachable anyway).
                    let t = self.iteration;
                    let (sd, sw) = (
                        self.variant.strategy_discount(t),
                        self.variant.strategy_weight(t),
                    );
                    // Lazy cumulative discount (B7): under sampled chance a
                    // (node, slab) is visited only on iterations whose turn
                    // card is sampled, so it catches up the discounts of the
                    // iterations L+1..t-1 skipped since its last visit L. The
                    // current iteration t's own discount stays the per-entry
                    // `d` / `sd` below. Under enumeration L = t-1 always, so
                    // both catch-ups are 1.0 (bit-identical to the plain
                    // update). Mirrors the turn+river solver. Read/update the
                    // last-visit slot before the `row` closure borrows `self`.
                    let last = self.last_discount_iter[node_id][cx];
                    self.last_discount_iter[node_id][cx] = t;
                    let s_catchup = self.variant.strategy_catchup(last, t);
                    let r_catchup_pos = self.regret_catchup(last, t, true);
                    let r_catchup_neg = self.regret_catchup(last, t, false);
                    let variant = self.variant;
                    let (dim, bmap) = self.row_map(node_id, ctx);
                    let row = |c: usize| bmap.map_or(c, |m| m[c] as usize);

                    let mut delta = vec![0.0f64; na * dim];
                    let mut sacc = vec![0.0f64; na * dim];
                    for c in 0..N {
                        let w = self.export_weight(traverser as usize, ctx.turn, ctx.river, c);
                        if w == 0.0 {
                            continue; // blocked / out-of-range: must not touch shared rows
                        }
                        let b = row(c);
                        for (a, av) in action_vals.iter().enumerate() {
                            delta[a * dim + b] += w * (av[c] - ev[c]);
                            sacc[a * dim + b] += reach[c] * strat[a * N + c];
                        }
                    }
                    // Only two regret-discount factors exist for a fixed t
                    // (selected by the sign of the stored regret); hoist the
                    // two `powf`s out of the row-entry loop (I1).
                    let (d_pos, d_neg) = variant.regret_discounts(t);
                    let reg = self.regrets[node_id].get_mut(cx);
                    for (i, d) in delta.iter().enumerate() {
                        let (disc, rc) = if reg[i] >= 0.0 {
                            (d_pos, r_catchup_pos)
                        } else {
                            (d_neg, r_catchup_neg)
                        };
                        let discounted = reg[i] * rc * disc;
                        reg[i] = variant.accumulate_regret(discounted, *d);
                    }
                    let ssum = self.strat_sum[node_id].get_mut(cx);
                    for (i, s) in sacc.iter().enumerate() {
                        ssum[i] = ssum[i] * s_catchup * sd + sw * s;
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
        // Sample one card by direct indexing — `stage_cards` would
        // materialize a 49/48-element Vec of which we use exactly one
        // element (I5). Index-identical to `stage_cards` (which has no
        // filtering), so the RNG stream and results are unchanged.
        let (n_pub, legal) = match deal_street {
            Street::Flop => (self.turns.len(), LEGAL_TURNS),
            Street::Turn => {
                let t = ctx.turn.expect("river deal requires a turn ctx");
                (self.rivers[t].len(), LEGAL_RIVERS)
            }
            s => unreachable!("chance deal on {s:?}"),
        };
        let idx = self.rng.next_index(n_pub);
        let card = match deal_street {
            Street::Flop => self.turns[idx],
            Street::Turn => self.rivers[ctx.turn.expect("river deal requires a turn ctx")][idx],
            s => unreachable!("chance deal on {s:?}"),
        };
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
    /// Unallocated slabs are uniform (zero regrets). Bucketed rows are
    /// regret-matched once per row and expanded to combos.
    fn node_strategy(&self, node_id: usize, ctx: Ctx, na: usize) -> Vec<f64> {
        let cx = self.ctx_index(node_id, ctx);
        let (dim, bmap) = self.row_map(node_id, ctx);
        let mut strat = vec![0.0; na * N];
        match self.regrets[node_id].get(cx) {
            Some(reg) => {
                let mut r = vec![0.0; na];
                let mut s = vec![0.0; na];
                let mut rows = vec![0.0; na * dim];
                for b in 0..dim {
                    for a in 0..na {
                        r[a] = reg[a * dim + b];
                    }
                    regret_matching(&r, &mut s);
                    for a in 0..na {
                        rows[a * dim + b] = s[a];
                    }
                }
                let row = |c: usize| bmap.map_or(c, |m| m[c] as usize);
                for c in 0..N {
                    let b = row(c);
                    for a in 0..na {
                        strat[a * N + c] = rows[a * dim + b];
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
    /// Bucketed river rows resolve through the combo→bucket map.
    pub fn average_strategy(
        &self,
        node_id: usize,
        turn_ctx: Option<usize>,
        river_ctx: Option<usize>,
        combo: usize,
    ) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        let ctx = Ctx {
            turn: turn_ctx,
            river: river_ctx,
        };
        let cx = self.ctx_index(node_id, ctx);
        let (dim, bmap) = self.row_map(node_id, ctx);
        let b = bmap.map_or(combo, |m| m[combo] as usize);
        match self.strat_sum[node_id].get(cx) {
            Some(ssum) => {
                let total: f64 = (0..na).map(|a| ssum[a * dim + b]).sum();
                if total > 0.0 {
                    (0..na).map(|a| ssum[a * dim + b] / total).collect()
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
    /// best-response time on flop trees (49×48 contexts). Bucketed rows
    /// normalize once per row and expand to combos.
    fn avg_matrix(&self, node_id: usize, ctx: Ctx, na: usize) -> Vec<f64> {
        let cx = self.ctx_index(node_id, ctx);
        let (dim, bmap) = self.row_map(node_id, ctx);
        let mut strat = vec![1.0 / na as f64; na * N];
        if let Some(ssum) = self.strat_sum[node_id].get(cx) {
            let mut rows = vec![1.0 / na as f64; na * dim];
            for b in 0..dim {
                let total: f64 = (0..na).map(|a| ssum[a * dim + b]).sum();
                if total > 0.0 {
                    for a in 0..na {
                        rows[a * dim + b] = ssum[a * dim + b] / total;
                    }
                }
            }
            let row = |c: usize| bmap.map_or(c, |m| m[c] as usize);
            for c in 0..N {
                let b = row(c);
                for a in 0..na {
                    strat[a * N + c] = rows[a * dim + b];
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
            NodeKind::NextStreet { .. } => unreachable!("flop trees have no NextStreet nodes"),
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
            NodeKind::NextStreet { .. } => unreachable!("flop trees have no NextStreet nodes"),
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
        ExplReport::zero_sum(br_value)
    }
}
