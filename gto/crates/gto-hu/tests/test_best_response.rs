use gto_hu::games::Kuhn;
use gto_hu::solver::{CfrVariant, ScalarCfr};
use gto_hu::validation::{best_response_value, exploitability};

#[test]
fn best_response_exploits_uniform_strategy() {
    // Against an untrained (uniform) strategy, BR must gain strictly more
    // than the Nash value from each side.
    let game = Kuhn;
    let cfr = ScalarCfr::new(&game, CfrVariant::Vanilla); // no iterations
    let br0 = best_response_value(&game, &cfr, 0);
    let br1 = best_response_value(&game, &cfr, 1);
    eprintln!("BR vs uniform: BR0={br0:.4} BR1={br1:.4}");
    assert!(br0 > -1.0 / 18.0 + 0.05, "BR0 {br0:.4} must exploit uniform");
    assert!(br1 > 1.0 / 18.0 + 0.05, "BR1 {br1:.4} must exploit uniform");
}

#[test]
fn exploitability_is_nonnegative_and_decreases() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(100);
    let e100 = exploitability(&game, &cfr);
    cfr.run(4_900);
    let e5000 = exploitability(&game, &cfr);
    eprintln!("exploitability: 100 iters={e100:.5} → 5000 iters={e5000:.5}");
    assert!(e100 >= -1e-9 && e5000 >= -1e-9);
    assert!(e5000 < e100, "exploitability must decrease: {e100:.5} → {e5000:.5}");
}

/// Encode a pure strategy for player 1 ("full nit": always fold to a bet,
/// never bet after a check) and verify BR0 = 1.0 exactly: P0 bets any card,
/// P1 folds, P0 wins the 1-chip ante every deal.
#[test]
fn best_response_exact_against_full_nit() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(1); // materialize all infoset nodes
    for (_key, node) in cfr.nodes.iter_mut() {
        // P1 keys: "1|{card}|b" (facing bet: 0=fold) and "1|{card}|p"
        // (after check: 0=check). Actions are [pass, bet].
        if _key.starts_with("1|") {
            node.strat_sum[0] = 1.0;
            node.strat_sum[1] = 0.0;
        }
    }
    let br0 = best_response_value(&game, &cfr, 0);
    assert!((br0 - 1.0).abs() < 1e-9, "BR0 vs full nit = {br0}, want exactly 1.0");
}

/// Against the uniform strategy the hand-computed values are
/// BR0 = 0.5 and BR1 = 1.25/3 (enumerate the 6 deals by hand).
#[test]
fn best_response_exact_against_uniform() {
    let game = Kuhn;
    let cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default()); // no iterations → uniform fallback
    let br0 = best_response_value(&game, &cfr, 0);
    let br1 = best_response_value(&game, &cfr, 1);
    assert!((br0 - 0.5).abs() < 1e-9, "BR0 vs uniform = {br0}, want 0.5");
    assert!((br1 - 1.25 / 3.0).abs() < 1e-9, "BR1 vs uniform = {br1}, want 1.25/3");
}
