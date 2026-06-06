use gto_hu::solver::{regret_matching, CfrVariant};

#[test]
fn regret_matching_normalizes_positive_regrets() {
    let mut s = vec![0.0; 3];
    regret_matching(&[3.0, 1.0, -2.0], &mut s);
    assert!((s[0] - 0.75).abs() < 1e-12);
    assert!((s[1] - 0.25).abs() < 1e-12);
    assert_eq!(s[2], 0.0);
}

#[test]
fn regret_matching_uniform_when_no_positive_regret() {
    let mut s = vec![0.0; 4];
    regret_matching(&[-1.0, 0.0, -5.0, 0.0], &mut s);
    for &p in &s {
        assert!((p - 0.25).abs() < 1e-12);
    }
}

#[test]
fn cfr_plus_clips_regret_at_zero() {
    let v = CfrVariant::CfrPlus { avg_delay: 0, linear_weighting: true };
    assert_eq!(v.accumulate_regret(1.0, -5.0), 0.0);
    assert_eq!(v.accumulate_regret(1.0, 2.0), 3.0);
}

#[test]
fn dcfr_discounts_positive_and_negative_differently() {
    let v = CfrVariant::Dcfr { alpha: 1.5, beta: 0.0, gamma: 2.0 };
    let t = 4u32;
    // positive: factor t^1.5/(t^1.5+1) = 8/9
    assert!((v.regret_discount(1.0, t) - 8.0 / 9.0).abs() < 1e-12);
    // negative: factor t^0/(t^0+1) = 0.5
    assert!((v.regret_discount(-1.0, t) - 0.5).abs() < 1e-12);
    // vanilla/CFR+ never discount
    assert_eq!(CfrVariant::Vanilla.regret_discount(-3.0, t), 1.0);
    let plus = CfrVariant::cfr_plus_default();
    assert_eq!(plus.regret_discount(5.0, t), 1.0);
    // accumulation is plain addition for DCFR
    assert!((v.accumulate_regret(8.0 / 9.0, 1.0) - (8.0 / 9.0 + 1.0)).abs() < 1e-12);
}

#[test]
fn cfr_plus_linear_weighting_and_delay() {
    let v = CfrVariant::CfrPlus { avg_delay: 5, linear_weighting: true };
    assert_eq!(v.strategy_weight(3), 0.0);
    assert_eq!(v.strategy_weight(6), 1.0);
    assert_eq!(v.strategy_weight(15), 10.0);
}
