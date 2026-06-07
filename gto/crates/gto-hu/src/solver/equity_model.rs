//! Preflop all-in equity model — the "simplified postflop value model"
//! of design spec §13 Phase 5. `NextStreet` leaves of the standalone
//! preflop tree pay `eq(hero, villain) × pot − contrib`, i.e. both
//! players are assumed to realize their all-in equity (realization = 1).
//!
//! The table is built by seeded Monte-Carlo runouts and is then treated
//! as the GROUND TRUTH of the simplified game: best response and
//! exploitability are exact relative to this table. The table itself is
//! an approximation of true equity (per-pair standard error ≈
//! 0.5/√samples), which is fine for its stated debugging purpose; the
//! full blueprint (Phase 6) replaces the model with real postflop
//! subtrees.

use gto_core::eval::evaluate_best;

use super::rng::SplitMix64;
use crate::ranges::{all_combos, NUM_COMBOS};

const N: usize = NUM_COMBOS;

/// Dense 1326×1326 hero-vs-villain equity. Entries for clashing combos
/// (shared cards) are never read by the solvers and hold 0.5.
pub struct EquityTable {
    eq: Vec<f32>,
}

impl EquityTable {
    /// Build from an arbitrary function (tests / toy games). The function
    /// is queried once per unordered pair (a < b) and mirrored as 1 − e,
    /// so any input yields a consistent zero-sum table.
    pub fn from_fn(mut f: impl FnMut(usize, usize) -> f32) -> Self {
        let mut eq = vec![0.5f32; N * N];
        for a in 0..N {
            for b in (a + 1)..N {
                let e = f(a, b);
                debug_assert!((0.0..=1.0).contains(&e), "equity must be in [0,1]");
                eq[a * N + b] = e;
                eq[b * N + a] = 1.0 - e;
            }
        }
        EquityTable { eq }
    }

    /// Seeded Monte-Carlo table over all non-clashing combo pairs.
    /// Each pair gets its own deterministic stream, so the table is
    /// identical regardless of thread count or iteration order
    /// (rayon-parallel over rows; ~40 s at 200 samples on 20 cores,
    /// was 644 s single-threaded).
    pub fn monte_carlo(seed: u64, samples: u32) -> Self {
        use rayon::prelude::*;
        assert!(samples > 0, "samples must be positive");
        let combos = all_combos();
        // Compute each row's upper triangle independently, then mirror.
        let rows: Vec<Vec<f32>> = (0..N)
            .into_par_iter()
            .map(|a| {
                let mut row = vec![0.5f32; N];
                let (a0, a1) = combos[a];
                for (b, item) in row.iter_mut().enumerate().skip(a + 1) {
                    let (b0, b1) = combos[b];
                    if a0 == b0 || a0 == b1 || a1 == b0 || a1 == b1 {
                        continue; // clash: never dealt against each other
                    }
                    *item = pair_equity_mc(combos[a], combos[b], pair_seed(seed, a, b), samples);
                }
                row
            })
            .collect();
        let mut eq = vec![0.5f32; N * N];
        for a in 0..N {
            for b in (a + 1)..N {
                let e = rows[a][b];
                eq[a * N + b] = e;
                eq[b * N + a] = 1.0 - e;
            }
        }
        EquityTable { eq }
    }

    #[inline]
    pub fn eq(&self, hero: usize, villain: usize) -> f32 {
        self.eq[hero * N + villain]
    }
}

/// Per-pair stream: decorrelated from neighbours, stable across orders.
fn pair_seed(seed: u64, a: usize, b: usize) -> u64 {
    // One SplitMix64 step over the pair id is itself a good mixer.
    SplitMix64::new(seed ^ ((a * N + b) as u64)).next_u64()
}

/// Monte-Carlo all-in equity of `hero` vs `villain` over `samples`
/// seeded 5-card runouts (win = 1, tie = 0.5).
pub fn pair_equity_mc(hero: (u8, u8), villain: (u8, u8), seed: u64, samples: u32) -> f32 {
    let mut deck: Vec<u8> = (0..52u8)
        .filter(|&c| c != hero.0 && c != hero.1 && c != villain.0 && c != villain.1)
        .collect();
    debug_assert_eq!(deck.len(), 48);
    let mut rng = SplitMix64::new(seed);
    let mut score = 0.0f64;
    let mut cards = [0u8; 7];
    for _ in 0..samples {
        // Partial Fisher–Yates: first 5 entries become the board.
        for i in 0..5 {
            let j = i + rng.next_index(48 - i);
            deck.swap(i, j);
        }
        cards[2..7].copy_from_slice(&deck[..5]);
        cards[0] = hero.0;
        cards[1] = hero.1;
        let sh = evaluate_best(&cards);
        cards[0] = villain.0;
        cards[1] = villain.1;
        let sv = evaluate_best(&cards);
        score += match sh.cmp(&sv) {
            std::cmp::Ordering::Greater => 1.0,
            std::cmp::Ordering::Equal => 0.5,
            std::cmp::Ordering::Less => 0.0,
        };
    }
    (score / samples as f64) as f32
}
