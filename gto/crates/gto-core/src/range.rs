/// Range: a probability distribution over the 1326 hole-card combos.
/// Each combo is (card_a, card_b) with card_a < card_b.

use crate::eval::Card;

pub const NUM_COMBOS: usize = 1326; // C(52,2)

/// Index of combo (a,b) where a < b.
#[inline]
pub fn combo_index(a: Card, b: Card) -> usize {
    let (lo, hi) = if a < b { (a, b) } else { (b, a) };
    let lo = lo as usize;
    let hi = hi as usize;
    // sum of (51 + 50 + ... + (52-lo)) + (hi - lo - 1)
    lo * 51 - lo * (lo - 1) / 2 + hi - lo - 1
}

/// All combos as (a, b) pairs, in index order.
pub fn all_combos() -> Vec<(Card, Card)> {
    let mut out = Vec::with_capacity(NUM_COMBOS);
    for a in 0u8..51 {
        for b in (a+1)..52 {
            out.push((a, b));
        }
    }
    out
}

/// A range: weight[combo_index] ∈ [0.0, 1.0]
#[derive(Clone)]
pub struct Range {
    pub weights: [f64; NUM_COMBOS],
}

impl Range {
    pub fn new_uniform() -> Self {
        Self { weights: [1.0; NUM_COMBOS] }
    }

    pub fn new_empty() -> Self {
        Self { weights: [0.0; NUM_COMBOS] }
    }

    /// Remove combos that conflict with dead cards (board, villain's hand).
    pub fn remove_blockers(&mut self, dead: &[Card]) {
        let combos = all_combos();
        for (i, (a, b)) in combos.iter().enumerate() {
            if dead.contains(a) || dead.contains(b) {
                self.weights[i] = 0.0;
            }
        }
    }

    pub fn total_weight(&self) -> f64 {
        self.weights.iter().sum()
    }
}
