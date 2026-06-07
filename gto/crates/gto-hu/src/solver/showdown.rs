//! Blocker-exact showdown machinery shared by the vector solvers.

use gto_core::eval::showdown_strengths;

use crate::ranges::NUM_COMBOS;

const N: usize = NUM_COMBOS;

/// Per-board combo strengths with the O(N) two-sweep win/lose difference.
pub struct ShowdownTable {
    strengths: Vec<u16>,
    /// Combo indices with strength > 0, sorted ascending by strength.
    sorted_idx: Vec<usize>,
}

impl ShowdownTable {
    pub fn new(board: &[u8; 5]) -> Self {
        let strengths = showdown_strengths(board);
        let mut sorted_idx: Vec<usize> = (0..N).filter(|&i| strengths[i] > 0).collect();
        sorted_idx.sort_unstable_by_key(|&i| strengths[i]);
        ShowdownTable {
            strengths,
            sorted_idx,
        }
    }

    /// Strength-percentile buckets for strategy-space abstraction
    /// (bucketing design spec §3): combos with `strength > 0` are walked
    /// in ascending-strength tier groups; every member of a tier gets
    /// `tier_start_rank * k / n_ranked`, so buckets are monotone in
    /// strength, equal strengths share a bucket, ties never straddle a
    /// boundary, and all buckets are < k. Board-blocked combos
    /// (strength 0) get bucket 0 — their reach is zero everywhere.
    pub fn strength_buckets(&self, k: usize) -> Vec<u16> {
        assert!(k > 0 && k <= u16::MAX as usize + 1, "bucket count {k} out of range");
        let idx = &self.sorted_idx;
        let n_ranked = idx.len().max(1);
        let mut buckets = vec![0u16; N];
        let mut g = 0;
        while g < idx.len() {
            let s = self.strengths[idx[g]];
            let mut h = g;
            while h < idx.len() && self.strengths[idx[h]] == s {
                h += 1;
            }
            let b = (g * k / n_ranked) as u16;
            for &i in &idx[g..h] {
                buckets[i] = b;
            }
            g = h;
        }
        buckets
    }

    /// Strength percentile per combo in (0, 1): tier-grouped MID-rank
    /// over the combos with `strength > 0` (same tie discipline as
    /// `strength_buckets`; +0.5 keeps the weakest tier strictly positive
    /// so 0.0 unambiguously marks board-blocked combos). The per-river
    /// feature of the turn bucketing score.
    pub fn strength_percentiles(&self) -> Vec<f32> {
        let idx = &self.sorted_idx;
        let n_ranked = idx.len().max(1) as f32;
        let mut pct = vec![0.0f32; N];
        let mut g = 0;
        while g < idx.len() {
            let s = self.strengths[idx[g]];
            let mut h = g;
            while h < idx.len() && self.strengths[idx[h]] == s {
                h += 1;
            }
            let p = (g as f32 + 0.5) / n_ranked;
            for &i in &idx[g..h] {
                pct[i] = p;
            }
            g = h;
        }
        pct
    }

    /// win_w − lose_w per combo against `opp_reach`, blocker-exact. O(N).
    pub fn diff(&self, combos: &[(u8, u8)], opp_reach: &[f64; N]) -> Vec<f64> {
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
}

/// For each combo c: Σ over opponent combos compatible with c of their
/// weight (total − per-card sums + own-combo weight added back).
pub fn weighted_compat(combos: &[(u8, u8)], opp_reach: &[f64; N]) -> Vec<f64> {
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
