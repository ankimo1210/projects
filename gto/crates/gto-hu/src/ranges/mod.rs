//! Range handling. The 1326-combo representation comes from gto-core.

pub use gto_core::range::{all_combos, combo_index, Range, NUM_COMBOS};
pub use gto_core::variant::{Nlhe, PokerVariant};

use std::sync::OnceLock;

/// The shared NLHE variant instance. M1 thin seam: solvers obtain combo
/// lists / strengths / blocker masks through this rather than calling
/// gto-core free functions directly.
pub fn nlhe() -> &'static Nlhe {
    static NLHE: OnceLock<Nlhe> = OnceLock::new();
    NLHE.get_or_init(Nlhe::new)
}

/// Uniform range with board blockers removed.
pub fn uniform_excluding(board: &[u8]) -> Range {
    let mut r = Range::new_uniform();
    r.remove_blockers(board);
    r
}
