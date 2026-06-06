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
