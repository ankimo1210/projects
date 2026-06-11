//! Game-variant seam: what a poker variant defines about hole cards.
//! NLHE is the only implementation (M1 thin seam). PLO arrives via the M4
//! experiment, which ALSO requires the runtime-length range refactor
//! ([f64; NUM_COMBOS] arrays) and k-card blocker inclusion-exclusion —
//! deliberately out of scope here (mode-matrix spec section 4.3).

use crate::eval::showdown_strengths;
use crate::range::{all_combos, NUM_COMBOS};

pub trait PokerVariant {
    type HoleCards: Copy;
    fn combo_count(&self) -> usize;
    fn combo_cards(&self, i: usize) -> Self::HoleCards;
    /// 52-bit card-occupancy mask for blocker tests.
    fn blocker_mask(&self, h: &Self::HoleCards) -> u64;
    /// Strength of every combo on `board` (0 = blocked / invalid).
    fn showdown_strengths(&self, board: &[u8]) -> Vec<u16>;
}

pub struct Nlhe {
    combos: Vec<(u8, u8)>,
}

impl Nlhe {
    pub fn new() -> Self {
        Nlhe { combos: all_combos() }
    }

    /// Combo list in index order (the canonical NLHE (lo, hi) pairs).
    pub fn combos(&self) -> &[(u8, u8)] {
        &self.combos
    }
}

impl Default for Nlhe {
    fn default() -> Self {
        Self::new()
    }
}

impl PokerVariant for Nlhe {
    type HoleCards = (u8, u8);

    fn combo_count(&self) -> usize {
        NUM_COMBOS
    }

    fn combo_cards(&self, i: usize) -> (u8, u8) {
        self.combos[i]
    }

    fn blocker_mask(&self, h: &(u8, u8)) -> u64 {
        (1u64 << h.0) | (1u64 << h.1)
    }

    fn showdown_strengths(&self, board: &[u8]) -> Vec<u16> {
        showdown_strengths(board)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::range::combo_index;

    #[test]
    fn count_and_roundtrip() {
        let v = Nlhe::new();
        assert_eq!(v.combo_count(), 1326);
        for i in 0..v.combo_count() {
            let (a, b) = v.combo_cards(i);
            assert!(a < b);
            assert_eq!(combo_index(a, b), i);
        }
    }

    #[test]
    fn blocker_mask_has_exactly_two_bits() {
        let v = Nlhe::new();
        let m = v.blocker_mask(&(0, 51));
        assert_eq!(m.count_ones(), 2);
        assert_ne!(m & 1, 0);
        assert_ne!(m & (1 << 51), 0);
    }

    #[test]
    fn strengths_delegate_to_eval() {
        let v = Nlhe::new();
        let board = [0u8, 5, 10, 15, 20];
        assert_eq!(v.showdown_strengths(&board), showdown_strengths(&board));
    }
}
