//! Kuhn poker: cards J=0,Q=1,K=2; both ante 1. Nash: game value = −1/18,
//! P0 Q never bets, P1 K always calls, P1 Q calls 1/3, P1 J bluffs 1/3.

use gto_hu::games::Kuhn;
use gto_hu::solver::{CfrVariant, ScalarCfr};
use gto_hu::validation::{best_response_value, exploitability};

#[test]
fn kuhn_cfr_plus_reaches_nash() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(20_000);

    let expl = exploitability(&game, &cfr);
    eprintln!("kuhn_cfr_plus exploitability: {expl:.6}");
    assert!(expl < 0.005, "exploitability {expl:.6} should be < 0.005");

    // Game value to P0 ≈ −1/18 (measured via best responses bracketing it).
    let br1 = best_response_value(&game, &cfr, 1);
    eprintln!("kuhn_cfr_plus BR1 value: {br1:.6} (expected ≈ +1/18 = {:.6})", 1.0 / 18.0);
    assert!(
        (br1 - 1.0 / 18.0).abs() < 0.01,
        "BR1 value {br1:.6} should be ≈ +1/18"
    );

    // P0 with Q (card 1) never bets at the root.
    let s = cfr.average_strategy("0|1|", 2);
    eprintln!("P0 Q root: pass={:.4} bet={:.4}", s[0], s[1]);
    assert!(s[1] < 0.02, "P0 Q root bet freq {} should be ~0", s[1]);

    // P1 with K (card 2) always calls a bet.
    let s = cfr.average_strategy("1|2|b", 2);
    eprintln!("P1 K vs bet: fold={:.4} call={:.4}", s[0], s[1]);
    assert!(s[1] > 0.98, "P1 K call freq {} should be ~1", s[1]);

    // P1 with J (card 0) bluff-bets ~1/3 after a check.
    let s = cfr.average_strategy("1|0|p", 2);
    eprintln!("P1 J after check: pass={:.4} bet={:.4} (expected bet≈1/3)", s[0], s[1]);
    assert!((s[1] - 1.0 / 3.0).abs() < 0.05, "P1 J bluff {} ≈ 1/3", s[1]);
}

#[test]
fn kuhn_dcfr_also_converges() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::dcfr_default());
    cfr.run(20_000);
    let expl = exploitability(&game, &cfr);
    eprintln!("kuhn_dcfr exploitability: {expl:.6}");
    assert!(expl < 0.01, "DCFR exploitability {expl:.6} should be < 0.01");
}

#[test]
fn kuhn_average_strategies_sum_to_one() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(1_000);
    for (key, node) in &cfr.nodes {
        let s = cfr.average_strategy(key, node.regrets.len());
        let sum: f64 = s.iter().sum();
        assert!((sum - 1.0).abs() < 1e-9, "strategy at {key} sums to {sum}");
    }
}
