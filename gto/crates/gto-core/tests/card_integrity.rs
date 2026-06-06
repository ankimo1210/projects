//! Strict card-integrity tests: duplicates must be impossible or fatal.

use gto_core::eval::{evaluate_best, parse_card};
use gto_core::{all_combos, combo_index, full_deck, NUM_COMBOS};

#[test]
#[should_panic(expected = "duplicate card")]
fn evaluate_best_panics_on_duplicate_cards_in_debug() {
    let c = |s: &str| parse_card(s).unwrap();
    // 2c appears twice — exactly the historic phantom-card shape.
    let cards = [c("Ah"), c("Kd"), c("2c"), c("2c"), c("9h"), c("3s"), c("4d")];
    let _ = evaluate_best(&cards);
}

#[test]
#[should_panic(expected = "5..=7 cards")]
fn evaluate_best_rejects_short_input() {
    let c = |s: &str| parse_card(s).unwrap();
    let _ = evaluate_best(&[c("Ah"), c("Kd"), c("2c"), c("9h")]);
}

#[test]
fn full_deck_has_52_unique_cards() {
    let deck = full_deck();
    assert_eq!(deck.len(), 52);
    let mut seen = [false; 52];
    for card in deck {
        assert!(!seen[card.0 as usize], "duplicate card {}", card.0);
        seen[card.0 as usize] = true;
    }
}

#[test]
fn combo_index_is_a_bijection() {
    let combos = all_combos();
    assert_eq!(combos.len(), NUM_COMBOS);
    for (i, &(a, b)) in combos.iter().enumerate() {
        assert!(a < b, "combo {i} not ordered: ({a},{b})");
        assert_eq!(combo_index(a, b), i, "combo_index mismatch at {i}");
        assert_eq!(combo_index(b, a), i, "combo_index must be order-insensitive");
    }
}
