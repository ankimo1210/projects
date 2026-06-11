//! Exact-combo vector CFR for a fixed turn board. The river is a public
//! chance node: enumerated exactly (tests, exploitability) or sampled
//! (public chance sampling for larger runs). Design spec §6–§7.
//!
//! Chance math: for each (hero, villain) deal exactly 44 of the 48 public
//! river cards are legal (52 − 4 board − 2 − 2). Enumeration weights each
//! surviving card 1/44 (masks below make the per-deal count exactly 44).
//! Sampling draws uniform from the 48 public cards and scales by 48/44,
//! which is unbiased: E[v̂] = Σ_{r∉h} (1/48)(48/44) v_r = (1/44) Σ_{r∉h} v_r.

use super::regret::regret_matching;
use super::rng::SplitMix64;
use super::showdown::{weighted_compat, ShowdownTable};
use super::variant::CfrVariant;
use super::vector::ExplReport;
use crate::game::rake::RakeModel;
use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::game::Street;
use crate::ranges::{Range, NUM_COMBOS};
use crate::tree::{NodeKind, Tree};

const N: usize = NUM_COMBOS;

/// How the river chance node is expanded during traversal.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChanceMode {
    /// Every legal river card, weight 1/44 per deal. Exact; slow.
    Enumerate,
    /// One river card per chance-node visit, importance-scaled (unbiased).
    /// Deterministic for a given seed.
    Sample { seed: u64 },
}

pub struct TurnRiverSolver {
    pub tree: Tree,
    pub turn_board: [u8; 4],
    pub ranges: [Range; 2],
    pub variant: CfrVariant,
    pub mode: ChanceMode,
    /// Rake applied at terminals (RakeModel::NONE keeps the legacy
    /// zero-sum path bit-identical).
    rake: RakeModel,
    /// Legal public river cards (off the turn board), ascending.
    /// The index into this vec is the "card context" (ctx).
    rivers: Vec<u8>,
    /// Showdown table per river card (same index as `rivers`).
    tables: Vec<ShowdownTable>,
    /// [node] → flat tables. Turn action nodes: na*N. River action nodes:
    /// n_rivers*na*N (ctx-major). Other nodes: empty vecs.
    regrets: Vec<Vec<f64>>,
    strat_sum: Vec<Vec<f64>>,
    /// Last iteration in which a (node, ctx) slice's per-iteration discounts
    /// were applied. `[node]` is empty for non-action nodes, length 1 for
    /// turn action nodes, length `n_rivers` for river action nodes (ctx-
    /// major). Drives lazy cumulative discounting under sampled chance: a
    /// slice skipped on iterations L+1..t-1 catches up their discounts on
    /// its next visit at t (B7). Unused under enumeration (every slice is
    /// visited every iteration, so L = t-1 and the catch-up is a no-op).
    last_discount_iter: Vec<Vec<u32>>,
    /// Prefix products of the DCFR regret discount for positive / negative
    /// regrets: `regret_disc_prefix_pos[k] = ∏_{u=1..k} u^α/(u^α+1)` (neg
    /// uses β). Index 0 = 1.0. Built lazily up to `iteration`. The cumulative
    /// regret discount over a skipped gap L+1..t-1 (sign constant there) is
    /// `prefix[t-1] / prefix[L]`. Empty for non-DCFR variants (catch-up is
    /// always 1.0, so CFR+ stays bit-identical).
    regret_disc_prefix_pos: Vec<f64>,
    regret_disc_prefix_neg: Vec<f64>,
    rng: SplitMix64,
    iteration: u32,
    combos: Vec<(u8, u8)>,
}

#[inline]
fn combo_blocks(combo: (u8, u8), card: u8) -> bool {
    use crate::ranges::{nlhe, PokerVariant};
    nlhe().blocker_mask(&combo) & (1u64 << card) != 0
}

fn zero_card(combos: &[(u8, u8)], card: u8, weights: &mut [f64; N]) {
    for (i, &(a, b)) in combos.iter().enumerate() {
        if a == card || b == card {
            weights[i] = 0.0;
        }
    }
}

impl TurnRiverSolver {
    pub fn new(
        tree: Tree,
        turn_board: [u8; 4],
        ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
    ) -> Self {
        Self::with_rake(tree, turn_board, ranges, variant, mode, RakeModel::NONE)
    }

    pub fn with_rake(
        tree: Tree,
        turn_board: [u8; 4],
        mut ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
        rake: RakeModel,
    ) -> Self {
        assert_eq!(
            tree.nodes[0].state.street,
            Street::Turn,
            "root must be a turn node (build with build_turn_river_tree)"
        );
        let mut seen = [false; 52];
        for &c in &turn_board {
            assert!(!seen[c as usize], "duplicate card on turn board");
            seen[c as usize] = true;
        }
        for r in &mut ranges {
            r.remove_blockers(&turn_board);
        }
        let rivers: Vec<u8> = (0..52u8).filter(|c| !turn_board.contains(c)).collect();
        let tables: Vec<ShowdownTable> = rivers
            .iter()
            .map(|&r| {
                let mut b5 = [0u8; 5];
                b5[..4].copy_from_slice(&turn_board);
                b5[4] = r;
                ShowdownTable::new(&b5)
            })
            .collect();
        let n_rivers = rivers.len();
        let alloc = |tree: &Tree| -> Vec<Vec<f64>> {
            tree.nodes
                .iter()
                .map(|n| match n.kind {
                    NodeKind::Action { .. } => {
                        let ctx = if n.state.street == Street::River {
                            n_rivers
                        } else {
                            1
                        };
                        vec![0.0; ctx * n.children.len() * N]
                    }
                    _ => Vec::new(),
                })
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        // One last-visit scalar per (node, ctx) for lazy cumulative discount.
        let last_discount_iter: Vec<Vec<u32>> = tree
            .nodes
            .iter()
            .map(|n| match n.kind {
                NodeKind::Action { .. } => {
                    let ctx = if n.state.street == Street::River {
                        n_rivers
                    } else {
                        1
                    };
                    vec![0u32; ctx]
                }
                _ => Vec::new(),
            })
            .collect();
        let seed = match mode {
            ChanceMode::Sample { seed } => seed,
            ChanceMode::Enumerate => 0,
        };
        TurnRiverSolver {
            tree,
            turn_board,
            ranges,
            variant,
            mode,
            rake,
            rivers,
            tables,
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

    pub fn rivers(&self) -> &[u8] {
        &self.rivers
    }

    /// Total bytes held by regret + average-strategy tables.
    pub fn table_bytes(&self) -> usize {
        self.regrets
            .iter()
            .chain(self.strat_sum.iter())
            .map(|v| v.len() * 8)
            .sum()
    }

    /// Legal river cards per (hero, villain) deal: 52−4−2−2 = 44.
    fn legal_rivers_per_deal(&self) -> f64 {
        // Hole cards dead per deal: hero (2) + villain (2).
        const HOLE_CARDS_PER_DEAL: usize = 4;
        (self.rivers.len() - HOLE_CARDS_PER_DEAL) as f64
    }

    pub fn run(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            self.extend_regret_prefix(self.iteration);
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;
                self.traverse(0, traverser, &reach, &opp, None);
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

    /// Table offset for a node: river nodes are ctx-major per card.
    fn table_base(&self, node_id: usize, ctx: Option<usize>, na: usize) -> usize {
        if self.tree.nodes[node_id].state.street == Street::River {
            ctx.expect("river node requires a card context") * na * N
        } else {
            debug_assert!(ctx.is_none(), "turn nodes precede the river deal");
            0
        }
    }

    /// Counterfactual values (bb) for `traverser`'s combos.
    fn traverse(
        &mut self,
        node_id: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        ctx: Option<usize>,
    ) -> Vec<f64> {
        let kind = self.tree.nodes[node_id].kind;
        match kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let mut pay = fold_payoffs(&state, winner)[traverser as usize] as f64 / 100.0;
                if traverser == winner {
                    // Rake comes out of the won pot; the loser's payoff is
                    // its own contribution either way. A fold faces a bet, so
                    // the matched pot 2*min(contrib) excludes the uncalled bet
                    // that fold_payoffs returns to the winner — rake that, not
                    // the full pot.
                    let matched_pot = 2 * state.contrib[0].min(state.contrib[1]);
                    pay -= self.rake.rake_cbb(matched_pot, state.street) as f64 / 100.0;
                }
                let compat = weighted_compat(&self.combos, opp_reach);
                compat.iter().map(|w| pay * w).collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(traverser))[traverser as usize] as f64 / 100.0;
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                let diff = table.diff(&self.combos, opp_reach);
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
            NodeKind::Chance { child } => match self.mode {
                ChanceMode::Enumerate => self.chance_enumerate(child, traverser, reach, opp_reach),
                ChanceMode::Sample { .. } => self.chance_sample(child, traverser, reach, opp_reach),
            },
            NodeKind::NextStreet { .. } => unreachable!("turn+river trees have no NextStreet nodes"),
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let base = self.table_base(node_id, ctx, na);
                let strat = self.node_strategy(node_id, base, na);

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
                    // Per-iteration discount/update discipline. Under sampled
                    // chance a river (node, ctx) slice is visited on only a
                    // fraction of iterations; on each visit it must catch up
                    // the discounts of the iterations skipped since its last
                    // visit, else early iterations are over-weighted vs
                    // enumerate (B7). `slot` is this slice's last-visit
                    // iteration L; the catch-up covers L+1..t-1 (the current
                    // iteration t's own discount is the per-element `d` /
                    // `sd` below). Under enumeration L = t-1 every time, so
                    // both catch-ups are 1.0 and this is identical to the
                    // plain lazy-discount update.
                    let t = self.iteration;
                    let slot = ctx.unwrap_or(0);
                    let last = self.last_discount_iter[node_id][slot];
                    self.last_discount_iter[node_id][slot] = t;
                    let (sd, sw) = (
                        self.variant.strategy_discount(t),
                        self.variant.strategy_weight(t),
                    );
                    let s_catchup = self.variant.strategy_catchup(last, t);
                    let r_catchup_pos = self.regret_catchup(last, t, true);
                    let r_catchup_neg = self.regret_catchup(last, t, false);
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
                            let i = base + a * N + c;
                            let (d, rc) = if reg[i] >= 0.0 {
                                (d_pos, r_catchup_pos)
                            } else {
                                (d_neg, r_catchup_neg)
                            };
                            let discounted = reg[i] * rc * d;
                            reg[i] =
                                variant.accumulate_regret(discounted, action_vals[a][c] - ev[c]);
                            ssum[i] = ssum[i] * s_catchup * sd + sw * reach[c] * strat[a * N + c];
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

    fn chance_enumerate(
        &mut self,
        child: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let w = 1.0 / self.legal_rivers_per_deal();
        let n_pub = self.rivers.len();
        let mut ev = vec![0.0; N];
        for ctx in 0..n_pub {
            let card = self.rivers[ctx];
            let mut r = *reach;
            let mut o = *opp_reach;
            zero_card(&self.combos, card, &mut r);
            zero_card(&self.combos, card, &mut o);
            let v = self.traverse(child, traverser, &r, &o, Some(ctx));
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
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let n_pub = self.rivers.len();
        let ctx = self.rng.next_index(n_pub);
        let card = self.rivers[ctx];
        let scale = n_pub as f64 / self.legal_rivers_per_deal(); // 48/44
        let mut r = *reach;
        let mut o = *opp_reach;
        zero_card(&self.combos, card, &mut r);
        zero_card(&self.combos, card, &mut o);
        let v = self.traverse(child, traverser, &r, &o, Some(ctx));
        let mut ev = vec![0.0; N];
        for c in 0..N {
            if !combo_blocks(self.combos[c], card) {
                ev[c] = scale * v[c];
            }
        }
        ev
    }

    /// Current per-combo strategy at a (node, ctx): [action * N + combo].
    fn node_strategy(&self, node_id: usize, base: usize, na: usize) -> Vec<f64> {
        let reg = &self.regrets[node_id];
        let mut strat = vec![0.0; na * N];
        let mut r = vec![0.0; na];
        let mut s = vec![0.0; na];
        for c in 0..N {
            for a in 0..na {
                r[a] = reg[base + a * N + c];
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

    /// Range weight for exports: zero when the combo holds the context's
    /// river card (such infosets are unreachable and their tables junk).
    pub fn export_weight(&self, actor: usize, ctx: Option<usize>, combo: usize) -> f64 {
        if let Some(i) = ctx {
            if combo_blocks(self.combos[combo], self.rivers[i]) {
                return 0.0;
            }
        }
        self.ranges[actor].weights[combo]
    }

    /// Normalized average strategy for one combo at one (node, ctx).
    pub fn average_strategy(&self, node_id: usize, ctx: Option<usize>, combo: usize) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        let base = self.table_base(node_id, ctx, na);
        let ssum = &self.strat_sum[node_id];
        let total: f64 = (0..na).map(|a| ssum[base + a * N + combo]).sum();
        if total > 0.0 {
            (0..na)
                .map(|a| ssum[base + a * N + combo] / total)
                .collect()
        } else {
            vec![1.0 / na as f64; na]
        }
    }

    /// Normalized average strategy for ALL combos at a (node, ctx):
    /// [action * N + combo]. One slab pass — the per-combo
    /// `average_strategy` allocates a Vec per combo and dominates
    /// best-response / avg-value time on turn+river trees (48 river
    /// contexts per node), so the BR/eval paths use this instead (I2).
    /// Per-combo normalization is identical to `average_strategy`.
    fn avg_matrix(&self, node_id: usize, ctx: Option<usize>, na: usize) -> Vec<f64> {
        let base = self.table_base(node_id, ctx, na);
        let ssum = &self.strat_sum[node_id];
        let mut strat = vec![0.0; na * N];
        for c in 0..N {
            let total: f64 = (0..na).map(|a| ssum[base + a * N + c]).sum();
            if total > 0.0 {
                for a in 0..na {
                    strat[a * N + c] = ssum[base + a * N + c] / total;
                }
            } else {
                let u = 1.0 / na as f64;
                for a in 0..na {
                    strat[a * N + c] = u;
                }
            }
        }
        strat
    }

    /// Range-weighted aggregate strategy at a (node, ctx) for display.
    pub fn aggregate_strategy(&self, node_id: usize, ctx: Option<usize>) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[node_id];
        let actor = self.actor_at(node_id) as usize;
        let na = node.children.len();
        let mut freq = vec![0.0; na];
        let mut total = 0.0;
        for c in 0..N {
            let w = self.export_weight(actor, ctx, c);
            if w == 0.0 {
                continue;
            }
            let s = self.average_strategy(node_id, ctx, c);
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
    // The chance node is ALWAYS enumerated here, regardless of training
    // mode: exploitability and game value are exact.

    /// Counterfactual BR values for `br_player` (opponent plays the
    /// average strategy).
    fn br_values(
        &self,
        node_id: usize,
        br_player: u8,
        opp_reach: &[f64; N],
        ctx: Option<usize>,
    ) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let mut pay = fold_payoffs(&state, winner)[br_player as usize] as f64 / 100.0;
                if br_player == winner {
                    // Rake comes out of the won pot; the loser's payoff is
                    // its own contribution either way. A fold faces a bet, so
                    // the matched pot 2*min(contrib) excludes the uncalled bet
                    // that fold_payoffs returns to the winner — rake that, not
                    // the full pot.
                    let matched_pot = 2 * state.contrib[0].min(state.contrib[1]);
                    pay -= self.rake.rake_cbb(matched_pot, state.street) as f64 / 100.0;
                }
                let compat = weighted_compat(&self.combos, opp_reach);
                compat.iter().map(|w| pay * w).collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(br_player))[br_player as usize] as f64 / 100.0;
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                let diff = table.diff(&self.combos, opp_reach);
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
            NodeKind::Chance { child } => {
                let w = 1.0 / self.legal_rivers_per_deal();
                let mut ev = vec![0.0; N];
                for i in 0..self.rivers.len() {
                    let card = self.rivers[i];
                    let mut o = *opp_reach;
                    zero_card(&self.combos, card, &mut o);
                    let v = self.br_values(child, br_player, &o, Some(i));
                    for c in 0..N {
                        if !combo_blocks(self.combos[c], card) {
                            ev[c] += w * v[c];
                        }
                    }
                }
                ev
            }
            NodeKind::NextStreet { .. } => unreachable!("turn+river trees have no NextStreet nodes"),
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
        ctx: Option<usize>,
    ) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let mut pay = fold_payoffs(&state, winner)[player as usize] as f64 / 100.0;
                if player == winner {
                    // Rake comes out of the won pot; the loser's payoff is
                    // its own contribution either way. A fold faces a bet, so
                    // the matched pot 2*min(contrib) excludes the uncalled bet
                    // that fold_payoffs returns to the winner — rake that, not
                    // the full pot.
                    let matched_pot = 2 * state.contrib[0].min(state.contrib[1]);
                    pay -= self.rake.rake_cbb(matched_pot, state.street) as f64 / 100.0;
                }
                let compat = weighted_compat(&self.combos, opp_reach);
                compat.iter().map(|w| pay * w).collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb = showdown_payoffs(&state, Some(player))[player as usize] as f64 / 100.0;
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                let diff = table.diff(&self.combos, opp_reach);
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
            NodeKind::Chance { child } => {
                let w = 1.0 / self.legal_rivers_per_deal();
                let mut ev = vec![0.0; N];
                for i in 0..self.rivers.len() {
                    let card = self.rivers[i];
                    let mut o = *opp_reach;
                    zero_card(&self.combos, card, &mut o);
                    let v = self.avg_values(child, player, &o, Some(i));
                    for c in 0..N {
                        if !combo_blocks(self.combos[c], card) {
                            ev[c] += w * v[c];
                        }
                    }
                }
                ev
            }
            NodeKind::NextStreet { .. } => unreachable!("turn+river trees have no NextStreet nodes"),
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

    /// Game value (bb/hand) to `player` when both follow the converged
    /// average strategy. Always exact (chance enumerated), even when
    /// training used sampling. Same normalization as `exploitability_bb`.
    pub fn game_value(&self, player: u8) -> f64 {
        let own = self.ranges[player as usize].weights;
        let opp = self.ranges[1 - player as usize].weights;
        let vals = self.avg_values(0, player, &opp, None);
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

    /// Game value (bb/hand) to player 0 (SB/IP) under avg-vs-avg play.
    /// Always exact (chance enumerated), even when training used sampling.
    pub fn game_value_p0(&self) -> f64 {
        self.game_value(0)
    }

    /// General-sum exploitability: per-player BR gain vs the avg-vs-avg
    /// game value; NashConv = Σ gains. Unraked, NashConv = br0 + br1
    /// exactly (zero-sum identity) — that branch is bit-identical to the
    /// pre-rake formula. Always exact (chance enumerated), even when
    /// training used sampling.
    pub fn exploitability_bb(&self) -> ExplReport {
        let mut br_value = [0.0f64; 2];
        #[allow(clippy::needless_range_loop)]
        for p in 0..2usize {
            let own = self.ranges[p].weights;
            let opp = self.ranges[1 - p].weights;
            let vals = self.br_values(0, p as u8, &opp, None);
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
}
