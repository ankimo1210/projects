pub mod card;
pub mod equity;
pub mod eval;
pub mod range;
pub mod tree;
pub mod cfr;

// Re-exports for downstream crates
pub use card::{Card, Rank, Suit, HandRank, evaluate, full_deck};
pub use equity::{monte_carlo, parse_cards, EquityResult};
pub use eval::{evaluate7, evaluate_best, parse_card, showdown_strengths};
pub use range::{Range, all_combos, combo_index, NUM_COMBOS};
pub use tree::{Action, GameTree, Node, NodeKind, Street};
pub use cfr::CfrSolver;

// ---------------------------------------------------------------------------
// High-level solve API (mirrors gto-solver's top-level fn)
// ---------------------------------------------------------------------------

/// ⚠ Single-street approximation: flop/turn boards are solved as if the
/// hand ends after this street (NextStreet ≈ Showdown). Only river boards
/// produce correct equilibrium strategies. See `gto-hu` for the real
/// multistreet solver.
pub fn solve(
    pot_bb: f64,
    effective_stack_bb: f64,
    board_cards: &[&str],
    iterations: u32,
    _max_bets: u8,   // kept for API compat; tree now uses fixed 1-raise-per-street
) -> SolveResult {
    let board: Vec<eval::Card> = board_cards.iter()
        .filter_map(|s| parse_card(s))
        .collect();

    let pot   = (pot_bb * 100.0) as i64;
    let stack = (effective_stack_bb * 100.0) as i64;
    let game_tree = tree::GameTree::build(pot, stack, tree::Street::Flop);
    let ranges = [range::Range::new_uniform(), range::Range::new_uniform()];

    let mut solver = cfr::CfrSolver::new(game_tree, board, ranges);
    let exploitability = solver.run(iterations);
    let strategy       = solver.root_strategy();
    let combo_strats   = solver.combo_strategies();

    SolveResult { strategy, combo_strats, exploitability, iterations }
}

#[derive(Debug)]
pub struct SolveResult {
    pub strategy:     Vec<(String, f64)>,
    pub combo_strats: Vec<(usize, String, f64)>,
    pub exploitability: f64,
    pub iterations:   u32,
}
