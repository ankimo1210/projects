//! Range handling. The 1326-combo representation comes from gto-core.

pub use gto_core::range::{all_combos, combo_index, Range, NUM_COMBOS};

/// Uniform range with board blockers removed.
pub fn uniform_excluding(board: &[u8]) -> Range {
    let mut r = Range::new_uniform();
    r.remove_blockers(board);
    r
}
