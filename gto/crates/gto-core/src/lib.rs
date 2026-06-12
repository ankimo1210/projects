pub mod card;
pub mod equity;
pub mod eval;
pub mod range;
pub mod variant;

// Re-exports for downstream crates
pub use card::{Card, Rank, Suit, HandRank, evaluate, full_deck};
pub use equity::{monte_carlo, parse_cards, EquityResult};
pub use eval::{evaluate7, evaluate_best, parse_card, showdown_strengths};
pub use range::{Range, all_combos, combo_index, NUM_COMBOS};
pub use variant::{Nlhe, PokerVariant};


