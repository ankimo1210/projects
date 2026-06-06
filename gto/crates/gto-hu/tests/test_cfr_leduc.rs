//! Leduc hold'em: 6 cards (J,Q,K ×2), ante 1, two betting rounds
//! (bet 2 then 4, max 2 raises/round), one public card. Pair beats rank.
//! Known game value ≈ −0.0856 for player 0 (OpenSpiel reference).

use gto_hu::games::Leduc;
use gto_hu::solver::{CfrVariant, ScalarCfr};
use gto_hu::validation::{best_response_value, exploitability};

#[test]
fn leduc_exploitability_decreases_and_gets_small() {
    let game = Leduc;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(200);
    let e200 = exploitability(&game, &cfr);
    cfr.run(1_800);
    let e2000 = exploitability(&game, &cfr);
    assert_eq!(
        cfr.nodes.len(),
        288,
        "Leduc infoset count: encoding regression"
    );
    eprintln!("Leduc infosets after 2000 iters: {}", cfr.nodes.len());
    eprintln!("Leduc exploitability: e200={e200:.4}, e2000={e2000:.4}");
    assert!(
        e2000 < e200,
        "exploitability must decrease: {e200:.4} → {e2000:.4}"
    );
    assert!(e2000 < 0.1, "exploitability after 2000 iters: {e2000:.4}");
}

#[test]
fn leduc_game_value_in_known_band() {
    let game = Leduc;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(5_000);
    // Bracket the value with the two best responses: at low exploitability
    // both are close to the true value (−0.0856 for P0 ⇒ +0.0856 for P1).
    let br1 = best_response_value(&game, &cfr, 1);
    eprintln!("Leduc BR1 at 5000 iters: {br1:.4}");
    assert!(
        (0.02..0.16).contains(&br1),
        "BR1 {br1:.4} should be near +0.0856"
    );
    let br0 = best_response_value(&game, &cfr, 0);
    eprintln!("Leduc BR0 at 5000 iters: {br0:.4}");
    assert!(
        (-0.16..-0.02).contains(&br0),
        "BR0 {br0:.4} should be near -0.0856"
    );
}

#[test]
fn leduc_chance_probabilities_sum_to_one() {
    use gto_hu::solver::Game;
    let game = Leduc;
    let root = game.root();
    let deals = game.chance_outcomes(&root);
    assert_eq!(deals.len(), 30, "6×5 ordered private deals");
    let total: f64 = deals.iter().map(|(_, p)| p).sum();
    assert!((total - 1.0).abs() < 1e-12);
}
